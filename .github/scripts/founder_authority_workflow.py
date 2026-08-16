#!/usr/bin/env python3
"""Trusted-base GitHub Actions adapter for the Founder Authority Guard.

This module is executed only after the workflow checks out the protected base
commit. It creates a check run on the exact pull-request head, collects immutable
GitHub evidence, evaluates the repository policy, and finalizes that same check.
A collection, validation, or finalization failure leaves no successful head-bound
check and therefore fails closed.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Any

from tools.founder_authority_guard import (
    GuardError,
    collect_changed_paths,
    evaluate,
    extract_issue_numbers,
    load_owner_identity,
)

API_VERSION = "2022-11-28"
CHECK_NAME = "founder-authority"
EVIDENCE_PATH = pathlib.Path("founder-authority-evidence.json")
MANIFEST_PATH = pathlib.Path("config/governance/owner_identity.v1.json")


class WorkflowError(RuntimeError):
    """Raised when trusted GitHub evidence cannot be collected or published."""


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorkflowError(f"{label} must be an object")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowError(f"{label} must be a non-empty string")
    return value.strip()


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise WorkflowError(f"{label} must be a positive integer")
    return value


class GitHubClient:
    def __init__(self, token: str, full_name: str) -> None:
        self.token = require_string(token, "GITHUB_TOKEN")
        self.full_name = require_string(full_name, "repository full name")
        if "/" not in self.full_name:
            raise WorkflowError("repository full name must be owner/name")
        self.owner_name, self.repository_name = self.full_name.split("/", 1)
        self.api_url = os.environ.get(
            "GITHUB_API_URL", "https://api.github.com"
        ).rstrip("/")
        self.graphql_url = os.environ.get(
            "GITHUB_GRAPHQL_URL", "https://api.github.com/graphql"
        )

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        }

    def repository_request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> Any:
        data = None
        headers = dict(self.headers)
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.api_url}/repos/{self.full_name}/{path}",
            data=data,
            method=method,
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def paginated(self, path: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        page = 1
        while True:
            separator = "&" if "?" in path else "?"
            batch = self.repository_request(
                f"{path}{separator}per_page=100&page={page}"
            )
            if not isinstance(batch, list):
                raise WorkflowError(
                    f"GitHub API path {path!r} did not return an array"
                )
            result.extend(item for item in batch if isinstance(item, dict))
            if len(batch) < 100:
                return result
            page += 1

    def graphql(self, query: str, variables: dict[str, object]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.graphql_url,
            data=json.dumps({"query": query, "variables": variables}).encode(
                "utf-8"
            ),
            method="POST",
            headers={**self.headers, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise WorkflowError("GitHub GraphQL returned an invalid response")
        if result.get("errors"):
            raise WorkflowError(
                f"GitHub GraphQL returned errors: {result['errors']}"
            )
        return require_mapping(result.get("data"), "GitHub GraphQL data")

    def create_head_check(self, head_sha: str) -> int:
        check = self.repository_request(
            "check-runs",
            method="POST",
            payload={
                "name": CHECK_NAME,
                "head_sha": head_sha,
                "status": "in_progress",
                "output": {
                    "title": "Founder Authority Guard",
                    "summary": (
                        "Trusted-base validation is running for this exact "
                        "pull-request head."
                    ),
                },
            },
        )
        check = require_mapping(check, "created check run")
        return require_int(check.get("id"), "created check-run ID")

    def finalize_head_check(
        self,
        check_run_id: int,
        *,
        success: bool,
        summary: str,
    ) -> None:
        conclusion = "success" if success else "failure"
        title = (
            "Founder Authority Guard passed"
            if success
            else "Founder Authority Guard failed closed"
        )
        self.repository_request(
            f"check-runs/{check_run_id}",
            method="PATCH",
            payload={
                "status": "completed",
                "conclusion": conclusion,
                "output": {"title": title, "summary": summary[-60000:]},
            },
        )


SIGNATURE_QUERY = """
query CommitSignature($owner: String!, $name: String!, $oid: GitObjectID!) {
  repository(owner: $owner, name: $name) {
    object(oid: $oid) {
      ... on Commit {
        signature {
          __typename
          isValid
          state
          verifiedAt
          wasSignedByGitHub
          signer { login databaseId }
          ... on GpgSignature { keyId }
          ... on SshSignature { keyFingerprint }
        }
      }
    }
  }
}
"""


def signature_for_commit(
    client: GitHubClient, sha: str, *, key_status: str
) -> dict[str, Any] | None:
    if key_status != "ACTIVE":
        return None
    data = client.graphql(
        SIGNATURE_QUERY,
        {
            "owner": client.owner_name,
            "name": client.repository_name,
            "oid": sha,
        },
    )
    repository = data.get("repository")
    obj = repository.get("object") if isinstance(repository, dict) else None
    signature = obj.get("signature") if isinstance(obj, dict) else None
    if signature is None:
        return None
    signature = require_mapping(signature, f"signature evidence for {sha}")
    signer = signature.get("signer")
    return {
        "type": signature.get("__typename"),
        "is_valid": signature.get("isValid"),
        "state": signature.get("state"),
        "verified_at": signature.get("verifiedAt"),
        "was_signed_by_github": signature.get("wasSignedByGitHub"),
        "signer": {
            "login": signer.get("login"),
            "id": signer.get("databaseId"),
        }
        if isinstance(signer, dict)
        else None,
        "key_fingerprint": signature.get("keyFingerprint"),
        "key_id": signature.get("keyId"),
    }


def collect_governance_issues(
    client: GitHubClient, body: str
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for number in extract_issue_numbers(body):
        try:
            issue = client.repository_request(f"issues/{number}")
        except urllib.error.HTTPError as exc:
            if exc.code not in {404, 410}:
                raise
            evidence.append(
                {
                    "number": number,
                    "exists": False,
                    "is_pull_request": False,
                    "state": None,
                    "labels": [],
                    "author": None,
                }
            )
            continue
        issue = require_mapping(issue, f"governance issue #{number}")
        labels = issue.get("labels") or []
        author = issue.get("user") or {}
        evidence.append(
            {
                "number": number,
                "exists": True,
                "is_pull_request": isinstance(issue.get("pull_request"), dict),
                "state": issue.get("state"),
                "labels": [
                    item.get("name")
                    for item in labels
                    if isinstance(item, dict)
                    and isinstance(item.get("name"), str)
                ],
                "author": {
                    "login": author.get("login"),
                    "id": author.get("id"),
                },
            }
        )
    return evidence


def collect_evidence(
    client: GitHubClient,
    event: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    pull = require_mapping(event.get("pull_request"), "pull_request payload")
    repository = require_mapping(event.get("repository"), "repository payload")
    pull_number = require_int(pull.get("number"), "pull request number")

    files = client.paginated(f"pulls/{pull_number}/files")
    reviews = client.paginated(f"pulls/{pull_number}/reviews")
    commits = client.paginated(f"pulls/{pull_number}/commits")

    owner = repository.get("owner") or {}
    author = pull.get("user") or {}
    base = pull.get("base") or {}
    head = pull.get("head") or {}
    body = pull.get("body") or ""
    if not isinstance(body, str):
        raise WorkflowError("pull request body must be a string")

    key_status = str(
        ((manifest.get("cryptographic_owner_keys") or {}).get("status")) or ""
    ).upper()

    commit_evidence: list[dict[str, Any]] = []
    for item in commits:
        sha = require_string(item.get("sha"), "pull-request commit SHA")
        if len(sha) != 40:
            raise WorkflowError("pull-request commit SHA must contain 40 characters")
        commit_evidence.append(
            {
                "sha": sha,
                "verification": (item.get("commit") or {}).get("verification")
                or {"verified": False, "reason": "missing_verification"},
                "author": {
                    "login": (item.get("author") or {}).get("login"),
                    "id": (item.get("author") or {}).get("id"),
                }
                if item.get("author")
                else None,
                "committer": {
                    "login": (item.get("committer") or {}).get("login"),
                    "id": (item.get("committer") or {}).get("id"),
                }
                if item.get("committer")
                else None,
                "signature": signature_for_commit(
                    client, sha, key_status=key_status
                ),
            }
        )

    return {
        "repository": {
            "full_name": repository.get("full_name"),
            "id": repository.get("id"),
            "owner": {"login": owner.get("login"), "id": owner.get("id")},
        },
        "pull_request": {
            "number": pull_number,
            "author": {
                "login": author.get("login"),
                "id": author.get("id"),
            },
            "body": body,
            "head_sha": head.get("sha"),
            "head_ref": head.get("ref"),
            "base_ref": base.get("ref"),
        },
        "changed_files": list(collect_changed_paths(files)),
        "governance_issues": collect_governance_issues(client, body),
        "reviews": [
            {
                "id": item.get("id"),
                "user": {
                    "login": (item.get("user") or {}).get("login"),
                    "id": (item.get("user") or {}).get("id"),
                },
                "state": item.get("state"),
                "commit_id": item.get("commit_id"),
                "submitted_at": item.get("submitted_at"),
            }
            for item in reviews
        ],
        "commits": commit_evidence,
    }


def decision_summary(decision: Any) -> str:
    lines = [
        "FOUNDER_AUTHORITY_GUARD: PASS",
        f"owner_authored={str(decision.owner_authored).lower()}",
        "protected_paths="
        + (",".join(decision.protected_paths) if decision.protected_paths else "none"),
        "owner_approval_required="
        + str(decision.owner_approval_required).lower(),
        "governance_issues="
        + (
            ",".join(f"#{number}" for number in decision.governance_issues)
            if decision.governance_issues
            else "none"
        ),
        f"owner_key_attested={str(decision.owner_key_attested).lower()}",
    ]
    lines.extend(f"WARNING: {warning}" for warning in decision.warnings)
    return "\n".join(lines)


def load_event() -> dict[str, Any]:
    event_path = pathlib.Path(
        require_string(os.environ.get("GITHUB_EVENT_PATH"), "GITHUB_EVENT_PATH")
    )
    try:
        return require_mapping(
            json.loads(event_path.read_text(encoding="utf-8")),
            "GitHub event",
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"cannot load GitHub event: {exc}") from exc


def run() -> int:
    event = load_event()
    repository = require_mapping(event.get("repository"), "repository payload")
    pull = require_mapping(event.get("pull_request"), "pull_request payload")
    full_name = require_string(repository.get("full_name"), "repository full name")
    head = require_mapping(pull.get("head"), "pull request head")
    head_sha = require_string(head.get("sha"), "pull request head SHA")
    if len(head_sha) != 40:
        raise WorkflowError("pull request head SHA must contain 40 characters")

    client = GitHubClient(os.environ.get("GITHUB_TOKEN", ""), full_name)
    check_run_id = client.create_head_check(head_sha)
    success = False
    summary = "Founder Authority Guard failed before producing a result."

    try:
        manifest = require_mapping(
            json.loads(MANIFEST_PATH.read_text(encoding="utf-8")),
            "owner identity manifest",
        )
        evidence = collect_evidence(client, event, manifest)
        EVIDENCE_PATH.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        EVIDENCE_PATH.chmod(0o600)
        owner = load_owner_identity(MANIFEST_PATH)
        decision = evaluate(evidence, manifest, owner)
        summary = decision_summary(decision)
        success = True
    except (
        OSError,
        json.JSONDecodeError,
        GuardError,
        WorkflowError,
        urllib.error.URLError,
    ) as exc:
        summary = f"FOUNDER_AUTHORITY_GUARD: FAIL: {exc}"
    finally:
        client.finalize_head_check(
            check_run_id,
            success=success,
            summary=summary,
        )

    print(summary, file=sys.stdout if success else sys.stderr)
    return 0 if success else 1


def main() -> int:
    try:
        return run()
    except (OSError, WorkflowError, urllib.error.URLError) as exc:
        print(f"FOUNDER_AUTHORITY_GUARD: FAIL CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
