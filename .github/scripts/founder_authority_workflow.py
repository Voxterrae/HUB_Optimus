#!/usr/bin/env python3
"""Trusted-base GitHub Actions adapter for the Founder Authority Guard.

This module executes only after the workflow checks out the protected base
commit. It evaluates immutable pull-request evidence and publishes the same
fail-closed result on both the exact pull-request head and GitHub's live test
merge commit. Success is published only while the head, base, merge candidate,
and semantic evidence remain unchanged.
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


def require_decimal_id(value: Any, label: str) -> int:
    if not isinstance(value, str):
        raise WorkflowError(f"{label} must be a positive decimal integer")
    text = value.strip()
    if not text or not text.isascii() or not text.isdecimal():
        raise WorkflowError(f"{label} must be a positive decimal integer")
    result = int(text)
    if result <= 0:
        raise WorkflowError(f"{label} must be a positive decimal integer")
    return result


def require_sha(value: Any, label: str) -> str:
    sha = require_string(value, label).lower()
    if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):
        raise WorkflowError(f"{label} must be a 40-character hexadecimal SHA")
    return sha


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
        expected_app_id = os.environ.get("FOUNDER_AUTHORITY_EXPECTED_APP_ID")
        expected_app_slug = os.environ.get("FOUNDER_AUTHORITY_EXPECTED_APP_SLUG")
        if (expected_app_id is None) != (expected_app_slug is None):
            raise WorkflowError(
                "FOUNDER_AUTHORITY_EXPECTED_APP_ID and "
                "FOUNDER_AUTHORITY_EXPECTED_APP_SLUG must be set together"
            )
        self.strict_check_publisher = expected_app_id is not None
        self.expected_check_app_id = (
            require_decimal_id(
                expected_app_id,
                "FOUNDER_AUTHORITY_EXPECTED_APP_ID",
            )
            if self.strict_check_publisher
            else None
        )
        self.expected_check_app_slug = (
            require_string(
                expected_app_slug,
                "FOUNDER_AUTHORITY_EXPECTED_APP_SLUG",
            )
            if self.strict_check_publisher
            else None
        )
        self.created_check_targets: dict[int, tuple[str, str]] = {}

    def require_expected_check(
        self,
        check: dict[str, Any],
        *,
        label: str,
        expected_head_sha: str | None = None,
    ) -> None:
        if not self.strict_check_publisher:
            raise WorkflowError(
                "strict check-publisher validation was not configured"
            )
        if check.get("name") != CHECK_NAME:
            raise WorkflowError(
                f"{label} has name {check.get('name')!r}, expected {CHECK_NAME!r}"
            )
        if expected_head_sha is not None:
            actual_head_sha = require_sha(check.get("head_sha"), f"{label} head SHA")
            if actual_head_sha != expected_head_sha:
                raise WorkflowError(
                    f"{label} targets {actual_head_sha}, expected {expected_head_sha}"
                )
        app = require_mapping(check.get("app"), f"{label} publisher app")
        app_id = require_int(app.get("id"), f"{label} publisher app ID")
        if app_id != self.expected_check_app_id:
            raise WorkflowError(
                f"{label} was published by GitHub App {app_id}, expected "
                f"{self.expected_check_app_id}"
            )
        app_slug = require_string(app.get("slug"), f"{label} publisher app slug")
        if app_slug != self.expected_check_app_slug:
            raise WorkflowError(
                f"{label} was published by GitHub App slug {app_slug!r}, expected "
                f"{self.expected_check_app_slug!r}"
            )

    def fail_invalid_created_check(
        self,
        check_run_id: int,
        *,
        reason: str,
    ) -> str | None:
        """Best-effort fail-close for a check created before validation failed."""

        try:
            check = self.repository_request(
                f"check-runs/{check_run_id}",
                method="PATCH",
                payload={
                    "status": "completed",
                    "conclusion": "failure",
                    "output": {
                        "title": "Founder Authority Guard failed closed",
                        "summary": (
                            "FOUNDER_AUTHORITY_GUARD: FAIL: invalid newly created "
                            f"check response: {reason}"
                        )[-60000:],
                    },
                },
            )
            check = require_mapping(
                check, f"failed-closed invalid check run {check_run_id}"
            )
            actual_id = require_int(
                check.get("id"), f"failed-closed check run {check_run_id} ID"
            )
            if actual_id != check_run_id:
                raise WorkflowError(
                    f"failed-closed response identified check {actual_id}, "
                    f"expected {check_run_id}"
                )
            if check.get("status") != "completed":
                raise WorkflowError(
                    f"failed-closed check run {check_run_id} is not completed"
                )
            if check.get("conclusion") != "failure":
                raise WorkflowError(
                    f"failed-closed check run {check_run_id} did not conclude failure"
                )
        except (
            OSError,
            json.JSONDecodeError,
            WorkflowError,
            urllib.error.URLError,
        ) as exc:
            return f"cannot fail-close invalid check {check_run_id}: {exc}"
        return None

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

    def create_check(self, target_sha: str, *, target_label: str) -> int:
        external_id: str | None = None
        if self.strict_check_publisher:
            target_sha = require_sha(target_sha, f"{target_label} target SHA")
            external_id = f"founder-authority:v1:{target_label}:{target_sha}"
        payload: dict[str, Any] = {
            "name": CHECK_NAME,
            "head_sha": target_sha,
            "status": "in_progress",
            "output": {
                "title": "Founder Authority Guard",
                "summary": (
                    "Trusted-base validation is running for the "
                    f"{target_label}."
                ),
            },
        }
        if external_id is not None:
            payload["external_id"] = external_id
        check = self.repository_request(
            "check-runs",
            method="POST",
            payload=payload,
        )
        check = require_mapping(check, f"created {target_label} check run")
        check_run_id = require_int(
            check.get("id"), f"created {target_label} check-run ID"
        )
        if not self.strict_check_publisher:
            return check_run_id

        assert external_id is not None
        try:
            self.require_expected_check(
                check,
                label=f"created {target_label} check run",
                expected_head_sha=target_sha,
            )
            if check.get("external_id") != external_id:
                raise WorkflowError(
                    f"created {target_label} check run has unexpected external ID"
                )
            if check.get("status") != "in_progress":
                raise WorkflowError(
                    f"created {target_label} check run is not in progress"
                )
            if check.get("conclusion") is not None:
                raise WorkflowError(
                    f"created {target_label} check run already has a conclusion"
                )
        except WorkflowError as exc:
            cleanup_error = self.fail_invalid_created_check(
                check_run_id,
                reason=str(exc),
            )
            suffix = f"; {cleanup_error}" if cleanup_error else ""
            raise WorkflowError(f"{exc}{suffix}") from exc

        self.created_check_targets[check_run_id] = (target_sha, external_id)
        return check_run_id

    def finalize_check(
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
        payload = {
            "status": "completed",
            "conclusion": conclusion,
            "output": {"title": title, "summary": summary[-60000:]},
        }
        if not self.strict_check_publisher:
            self.repository_request(
                f"check-runs/{check_run_id}",
                method="PATCH",
                payload=payload,
            )
            return

        target = self.created_check_targets.get(check_run_id)
        if target is None:
            raise WorkflowError(
                f"refusing to finalize unknown check run {check_run_id}"
            )
        expected_head_sha, expected_external_id = target
        check = self.repository_request(
            f"check-runs/{check_run_id}",
            method="PATCH",
            payload=payload,
        )
        check = require_mapping(check, f"finalized check run {check_run_id}")
        self.require_expected_check(
            check,
            label=f"finalized check run {check_run_id}",
            expected_head_sha=expected_head_sha,
        )
        actual_id = require_int(
            check.get("id"), f"finalized check run {check_run_id} ID"
        )
        if actual_id != check_run_id:
            raise WorkflowError(
                f"finalized response identified check {actual_id}, "
                f"expected {check_run_id}"
            )
        if check.get("external_id") != expected_external_id:
            raise WorkflowError(
                f"finalized check run {check_run_id} has unexpected external ID"
            )
        if check.get("status") != "completed":
            raise WorkflowError(
                f"finalized check run {check_run_id} is not completed"
            )
        if check.get("conclusion") != conclusion:
            raise WorkflowError(
                f"finalized check run {check_run_id} concluded "
                f"{check.get('conclusion')!r}, expected {conclusion!r}"
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


def live_pull_snapshot(
    client: GitHubClient,
    pull_number: int,
    *,
    expected_head_sha: str,
    expected_base_sha: str,
    expected_merge_sha: str | None = None,
) -> dict[str, Any]:
    pull = require_mapping(
        client.repository_request(f"pulls/{pull_number}"),
        f"live pull request #{pull_number}",
    )
    if pull.get("state") != "open" or pull.get("merged") is not False:
        raise WorkflowError("pull request must remain open and unmerged")

    head = require_mapping(pull.get("head"), "live pull-request head")
    base = require_mapping(pull.get("base"), "live pull-request base")
    head_sha = require_sha(head.get("sha"), "live pull-request head SHA")
    base_sha = require_sha(base.get("sha"), "live pull-request base SHA")
    merge_sha = require_sha(
        pull.get("merge_commit_sha"), "live test merge commit SHA"
    )

    if head_sha != expected_head_sha:
        raise WorkflowError(
            f"pull-request head changed: expected {expected_head_sha}, got {head_sha}"
        )
    if base_sha != expected_base_sha:
        raise WorkflowError(
            f"pull-request base changed: expected {expected_base_sha}, got {base_sha}"
        )
    if expected_merge_sha is not None and merge_sha != expected_merge_sha:
        raise WorkflowError(
            f"test merge commit changed: expected {expected_merge_sha}, got {merge_sha}"
        )
    if merge_sha in {head_sha, base_sha}:
        raise WorkflowError("test merge commit must differ from head and base")

    merge_commit = require_mapping(
        client.repository_request(f"commits/{merge_sha}"),
        "live test merge commit",
    )
    parents = merge_commit.get("parents")
    if not isinstance(parents, list):
        raise WorkflowError("live test merge commit parents must be an array")
    parent_shas = [
        require_sha(item.get("sha"), "test merge parent SHA")
        for item in parents
        if isinstance(item, dict)
    ]
    if parent_shas != [base_sha, head_sha]:
        raise WorkflowError(
            "test merge commit parents do not match the live base and head"
        )

    return {
        "pull": pull,
        "head_sha": head_sha,
        "base_sha": base_sha,
        "merge_sha": merge_sha,
    }


def semantic_fingerprint(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def finalize_created_checks(
    client: GitHubClient,
    checks: list[tuple[str, int]],
    *,
    success: bool,
    summary: str,
) -> list[str]:
    errors: list[str] = []
    for label, check_run_id in checks:
        try:
            client.finalize_check(
                check_run_id,
                success=success,
                summary=f"target={label}\n{summary}",
            )
        except (OSError, WorkflowError, urllib.error.URLError) as exc:
            errors.append(f"cannot finalize {label} check {check_run_id}: {exc}")
            break

    if not errors:
        return []

    failure_summary = (
        "FOUNDER_AUTHORITY_GUARD: FAIL: check publication failed; "
        "no created check may retain a successful conclusion.\n"
        + "\n".join(errors)
    )
    revocation_errors: list[str] = []
    for label, check_run_id in checks:
        try:
            client.finalize_check(
                check_run_id,
                success=False,
                summary=f"target={label}\n{failure_summary}",
            )
        except (OSError, WorkflowError, urllib.error.URLError) as exc:
            revocation_errors.append(
                f"cannot fail-close {label} check {check_run_id}: {exc}"
            )
    return [*errors, *revocation_errors]


def run() -> int:
    event = load_event()
    repository = require_mapping(event.get("repository"), "repository payload")
    event_pull = require_mapping(event.get("pull_request"), "pull_request payload")
    full_name = require_string(repository.get("full_name"), "repository full name")
    pull_number = require_int(event_pull.get("number"), "pull request number")
    event_head = require_mapping(event_pull.get("head"), "event pull-request head")
    event_base = require_mapping(event_pull.get("base"), "event pull-request base")
    expected_head_sha = require_sha(
        event_head.get("sha"), "event pull-request head SHA"
    )
    expected_base_sha = require_sha(
        event_base.get("sha"), "event pull-request base SHA"
    )

    client = GitHubClient(os.environ.get("GITHUB_TOKEN", ""), full_name)
    checks: list[tuple[str, int]] = []
    success = False
    summary = "Founder Authority Guard failed before producing a result."

    try:
        initial = live_pull_snapshot(
            client,
            pull_number,
            expected_head_sha=expected_head_sha,
            expected_base_sha=expected_base_sha,
        )
        checks.append(
            (
                "exact pull-request head",
                client.create_check(
                    initial["head_sha"], target_label="exact pull-request head"
                ),
            )
        )
        checks.append(
            (
                "live test merge commit",
                client.create_check(
                    initial["merge_sha"], target_label="live test merge commit"
                ),
            )
        )

        manifest = require_mapping(
            json.loads(MANIFEST_PATH.read_text(encoding="utf-8")),
            "owner identity manifest",
        )
        evaluation_event = dict(event)
        evaluation_event["pull_request"] = initial["pull"]
        evidence = collect_evidence(client, evaluation_event, manifest)
        evidence["evaluation_targets"] = {
            "head_sha": initial["head_sha"],
            "base_sha": initial["base_sha"],
            "merge_commit_sha": initial["merge_sha"],
        }
        EVIDENCE_PATH.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        EVIDENCE_PATH.chmod(0o600)

        owner = load_owner_identity(MANIFEST_PATH)
        decision = evaluate(evidence, manifest, owner)
        summary = decision_summary(decision)

        before_finalize = live_pull_snapshot(
            client,
            pull_number,
            expected_head_sha=initial["head_sha"],
            expected_base_sha=initial["base_sha"],
            expected_merge_sha=initial["merge_sha"],
        )
        verification_event = dict(event)
        verification_event["pull_request"] = before_finalize["pull"]
        verification_evidence = collect_evidence(
            client, verification_event, manifest
        )
        verification_evidence["evaluation_targets"] = evidence["evaluation_targets"]
        if semantic_fingerprint(verification_evidence) != semantic_fingerprint(evidence):
            raise WorkflowError(
                "semantic evidence changed after evaluation and before finalization"
            )

        live_pull_snapshot(
            client,
            pull_number,
            expected_head_sha=initial["head_sha"],
            expected_base_sha=initial["base_sha"],
            expected_merge_sha=initial["merge_sha"],
        )
        summary = (
            f"{summary}\n"
            f"head_sha={initial['head_sha']}\n"
            f"base_sha={initial['base_sha']}\n"
            f"merge_commit_sha={initial['merge_sha']}"
        )
        success = True
    except (
        OSError,
        json.JSONDecodeError,
        GuardError,
        WorkflowError,
        urllib.error.URLError,
    ) as exc:
        summary = f"FOUNDER_AUTHORITY_GUARD: FAIL: {exc}"

    finalization_errors = finalize_created_checks(
        client,
        checks,
        success=success,
        summary=summary,
    )
    if finalization_errors:
        success = False
        summary = f"{summary}\n" + "\n".join(finalization_errors)

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
