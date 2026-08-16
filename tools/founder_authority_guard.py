#!/usr/bin/env python3
"""Fail-closed governance guard for HUB_Optimus owner authority.

The guard does not prove a human's legal identity and cannot prevent account
compromise. It enforces the repository evidence that can be checked safely:

- immutable GitHub login and numeric user ID;
- protected-path pull-request and commit authorship by the owner identity;
- verified commits;
- owner-authored, governance-labelled issue linkage for protected changes;
- owner approval at the current head for non-owner contribution PRs;
- exact owner SSH signing-key fingerprint binding after key activation.

Private keys and signing secrets must never be stored in the repository.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Any, Iterable

DEFAULT_MANIFEST = pathlib.Path("config/governance/owner_identity.v1.json")
ISSUE_REFERENCE_RE = re.compile(
    r"(?im)^\s*(?:related\s+to|governance\s+issue)\s+#(?P<number>[1-9][0-9]*)\b"
)

# GitHub's web editor and merge UI may record the repository owner as the Git
# author while GitHub's immutable web-flow identity is the committer. No other
# non-owner committer is accepted for a protected-path pull request.
TRUSTED_GITHUB_COMMITTERS = frozenset({("web-flow", 19864447)})
STATE_CHANGING_REVIEW_STATES = frozenset(
    {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
)

# These prefixes are constitutional or control-plane surfaces. A non-owner may
# discuss them in an issue, but may not author a pull request that changes them.
PROTECTED_PREFIXES = (
    "docs/governance/",
    "config/governance/",
    ".github/",
)

PROTECTED_EXACT_PATHS = {
    "AGENTS.md",
    "ACKNOWLEDGEMENTS.md",
    "CONTRIBUTING.md",
    "IP_NOTICE.md",
    "KERNEL_CHARTER.md",
    "KERNEL_CHARTER_EN.md",
    "README.md",
    "docs/context/AI_HANDOFF.md",
    "docs/context/AI_HANDOFF_HISTORY_PRE_1862.md",
    "docs/context/OWNER_AUTHORITY_HANDOFF.md",
    "docs/context/SOURCE_OF_TRUTH.md",
    "tools/founder_authority_guard.py",
    "tests/test_founder_authority_guard.py",
}


class GuardError(RuntimeError):
    """Raised when evidence violates the founder-authority policy."""


@dataclass(frozen=True)
class OwnerIdentity:
    login: str
    user_id: int
    key_status: str
    key_fingerprints: tuple[str, ...]


@dataclass(frozen=True)
class GuardDecision:
    owner_authored: bool
    protected_paths: tuple[str, ...]
    owner_approval_required: bool
    governance_issues: tuple[int, ...]
    owner_key_attested: bool
    warnings: tuple[str, ...]


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GuardError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GuardError(f"{label} must be an array")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GuardError(f"{label} must be a non-empty string")
    return value.strip()


def _require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GuardError(f"{label} must be a positive integer")
    return value


def load_owner_identity(path: pathlib.Path = DEFAULT_MANIFEST) -> OwnerIdentity:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GuardError(f"owner identity manifest is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GuardError(f"owner identity manifest is invalid JSON: {exc}") from exc

    manifest = _require_mapping(manifest, "owner identity manifest")
    repository_identity = _require_mapping(
        manifest.get("repository_identity"), "repository_identity"
    )
    keys = _require_mapping(
        manifest.get("cryptographic_owner_keys"), "cryptographic_owner_keys"
    )
    fingerprints_raw = _require_list(keys.get("fingerprints"), "fingerprints")
    fingerprints: list[str] = []
    for index, value in enumerate(fingerprints_raw):
        fingerprint = _require_string(value, f"fingerprints[{index}]")
        if fingerprint in fingerprints:
            raise GuardError(f"duplicate owner key fingerprint: {fingerprint}")
        fingerprints.append(fingerprint)

    return OwnerIdentity(
        login=_require_string(repository_identity.get("login"), "repository login"),
        user_id=_require_int(
            repository_identity.get("immutable_user_id"), "repository user ID"
        ),
        key_status=_require_string(keys.get("status"), "owner key status"),
        key_fingerprints=tuple(fingerprints),
    )


def normalize_path(value: Any) -> str:
    path = _require_string(value, "changed file path").replace("\\", "/")
    pure = pathlib.PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or path.startswith("./"):
        raise GuardError(f"unsafe changed file path: {path!r}")
    normalized = pure.as_posix()
    if normalized in {"", "."}:
        raise GuardError("changed file path cannot be empty")
    return normalized


def collect_changed_paths(file_records: Iterable[Any]) -> tuple[str, ...]:
    """Return current and previous paths, preserving order and removing duplicates."""

    paths: list[str] = []
    for raw in file_records:
        record = _require_mapping(raw, "changed file record")
        for key in ("filename", "previous_filename"):
            value = record.get(key)
            if value is None:
                continue
            path = normalize_path(value)
            if path not in paths:
                paths.append(path)
    return tuple(paths)


def extract_issue_numbers(body: str) -> tuple[int, ...]:
    if not isinstance(body, str):
        raise GuardError("pull request body must be a string")
    numbers: list[int] = []
    for match in ISSUE_REFERENCE_RE.finditer(body):
        number = int(match.group("number"))
        if number not in numbers:
            numbers.append(number)
    return tuple(numbers)


def is_protected_path(path: str, manifest_paths: Iterable[str]) -> bool:
    if path in PROTECTED_EXACT_PATHS:
        return True
    if path.startswith(PROTECTED_PREFIXES):
        return True
    return path in set(manifest_paths)


def identity_matches(candidate: Any, owner: OwnerIdentity) -> bool:
    candidate = _require_mapping(candidate, "GitHub identity")
    return (
        candidate.get("login") == owner.login
        and candidate.get("id") == owner.user_id
    )


def _identity_is_trusted_committer(candidate: Any, owner: OwnerIdentity) -> bool:
    if identity_matches(candidate, owner):
        return True
    candidate = _require_mapping(candidate, "commit committer")
    return (candidate.get("login"), candidate.get("id")) in TRUSTED_GITHUB_COMMITTERS


def _effective_owner_review(
    reviews: list[Any], owner: OwnerIdentity
) -> dict[str, Any] | None:
    """Return the latest state-changing owner review.

    COMMENTED reviews are deliberately ignored because they do not revoke an
    existing approval. APPROVED, CHANGES_REQUESTED, and DISMISSED are effective
    state changes and the last one controls.
    """

    latest: dict[str, Any] | None = None
    for raw in reviews:
        review = _require_mapping(raw, "review")
        user = review.get("user")
        if not isinstance(user, dict) or not identity_matches(user, owner):
            continue
        state = str(review.get("state", "")).upper()
        if state in STATE_CHANGING_REVIEW_STATES:
            latest = review
    return latest


def _validate_verified_commits(commits: list[Any]) -> None:
    if not commits:
        raise GuardError("pull request evidence contains no commits")
    failures: list[str] = []
    for raw in commits:
        commit = _require_mapping(raw, "commit")
        sha = _require_string(commit.get("sha"), "commit SHA")
        verification = _require_mapping(commit.get("verification"), "verification")
        if verification.get("verified") is not True:
            reason = verification.get("reason") or "unverified"
            failures.append(f"{sha[:12]} ({reason})")
    if failures:
        raise GuardError(
            "all commits must be verified; failing commits: " + ", ".join(failures)
        )


def _validate_protected_commit_authorship(
    commits: list[Any], owner: OwnerIdentity
) -> None:
    failures: list[str] = []
    for raw in commits:
        commit = _require_mapping(raw, "commit")
        sha = _require_string(commit.get("sha"), "commit SHA")
        author = commit.get("author")
        committer = commit.get("committer")
        try:
            author_matches = identity_matches(author, owner)
        except GuardError:
            author_matches = False
        try:
            committer_matches = _identity_is_trusted_committer(committer, owner)
        except GuardError:
            committer_matches = False
        if not author_matches or not committer_matches:
            failures.append(sha[:12])
    if failures:
        raise GuardError(
            "every commit in a protected-path pull request must be owner-authored "
            "and owner-committed or committed by GitHub web-flow; failing commits: "
            + ", ".join(failures)
        )


def _validate_governance_issues(
    evidence: dict[str, Any], body: str, owner: OwnerIdentity
) -> tuple[int, ...]:
    referenced = extract_issue_numbers(body)
    if not referenced:
        raise GuardError(
            "constitutional/control-plane changes require an explicit 'Related to #N' "
            "or 'Governance issue #N' reference in the pull request body"
        )

    raw_issues = _require_list(evidence.get("governance_issues"), "governance_issues")
    issues_by_number: dict[int, dict[str, Any]] = {}
    for raw in raw_issues:
        issue = _require_mapping(raw, "governance issue")
        number = _require_int(issue.get("number"), "governance issue number")
        if number in issues_by_number:
            raise GuardError(f"duplicate governance issue evidence for #{number}")
        issues_by_number[number] = issue

    failures: list[str] = []
    for number in referenced:
        issue = issues_by_number.get(number)
        if issue is None or issue.get("exists") is not True:
            failures.append(f"#{number} does not exist")
            continue
        if issue.get("is_pull_request") is True:
            failures.append(f"#{number} is a pull request, not a governance issue")
            continue
        author = issue.get("author")
        try:
            author_matches = identity_matches(author, owner)
        except GuardError:
            author_matches = False
        if not author_matches:
            failures.append(f"#{number} is not owner-authored")
            continue
        labels = _require_list(issue.get("labels"), f"governance issue #{number} labels")
        normalized_labels = {
            _require_string(label, f"governance issue #{number} label").casefold()
            for label in labels
        }
        if "governance" not in normalized_labels:
            failures.append(f"#{number} is not labelled governance")

    if failures:
        raise GuardError("invalid governance issue linkage: " + "; ".join(failures))
    return referenced


def _validate_owner_key_attestation(
    commits: list[Any], owner: OwnerIdentity
) -> bool:
    if owner.key_status.upper() != "ACTIVE":
        return False
    if not owner.key_fingerprints:
        raise GuardError("owner key status is ACTIVE but no fingerprints are pinned")

    failures: list[str] = []
    for raw in commits:
        commit = _require_mapping(raw, "commit")
        sha = _require_string(commit.get("sha"), "commit SHA")
        signature = commit.get("signature")
        if not isinstance(signature, dict):
            failures.append(f"{sha[:12]} (missing signature evidence)")
            continue
        if signature.get("type") != "SshSignature":
            failures.append(f"{sha[:12]} (owner-key mode requires SSH signatures)")
            continue
        if signature.get("is_valid") is not True:
            failures.append(f"{sha[:12]} (invalid SSH signature)")
            continue
        if signature.get("was_signed_by_github") is True:
            failures.append(f"{sha[:12]} (signed by GitHub, not the owner key)")
            continue
        signer = signature.get("signer")
        try:
            signer_matches = identity_matches(signer, owner)
        except GuardError:
            signer_matches = False
        if not signer_matches:
            failures.append(f"{sha[:12]} (signature signer is not the owner)")
            continue
        fingerprint = signature.get("key_fingerprint")
        if fingerprint not in owner.key_fingerprints:
            failures.append(f"{sha[:12]} (unrecognized SSH fingerprint)")

    if failures:
        raise GuardError(
            "protected commits must be attested by a pinned owner SSH key; "
            + ", ".join(failures)
        )
    return True


def evaluate(
    evidence: dict[str, Any],
    manifest: dict[str, Any],
    owner: OwnerIdentity,
) -> GuardDecision:
    evidence = _require_mapping(evidence, "evidence")
    manifest = _require_mapping(manifest, "manifest")

    repository = _require_mapping(evidence.get("repository"), "repository")
    repository_owner = _require_mapping(repository.get("owner"), "repository owner")
    if not identity_matches(repository_owner, owner):
        raise GuardError(
            "repository owner identity does not match the pinned login and immutable user ID"
        )

    pull_request = _require_mapping(evidence.get("pull_request"), "pull_request")
    author = _require_mapping(pull_request.get("author"), "pull request author")
    head_sha = _require_string(pull_request.get("head_sha"), "head SHA")
    base_ref = _require_string(pull_request.get("base_ref"), "base ref")
    body = pull_request.get("body")
    if body is None:
        body = ""
    if not isinstance(body, str):
        raise GuardError("pull request body must be a string")
    if base_ref != "main":
        raise GuardError(f"owner-authority review must target main, not {base_ref!r}")

    changed_files = tuple(
        normalize_path(value)
        for value in _require_list(evidence.get("changed_files"), "changed_files")
    )
    if not changed_files:
        raise GuardError("pull request contains no changed files")

    manifest_paths = tuple(
        normalize_path(value)
        for value in _require_list(
            manifest.get("constitutional_files"), "constitutional_files"
        )
    )
    protected_paths = tuple(
        path for path in changed_files if is_protected_path(path, manifest_paths)
    )

    commits = _require_list(evidence.get("commits"), "commits")
    _validate_verified_commits(commits)

    owner_authored = identity_matches(author, owner)
    governance_issues: tuple[int, ...] = ()
    owner_key_attested = False
    if protected_paths:
        if not owner_authored:
            raise GuardError(
                "only the pinned owner identity may author constitutional/control-plane "
                "changes; protected paths: " + ", ".join(protected_paths)
            )
        _validate_protected_commit_authorship(commits, owner)
        governance_issues = _validate_governance_issues(evidence, body, owner)
        owner_key_attested = _validate_owner_key_attestation(commits, owner)

    owner_approval_required = not owner_authored
    if owner_approval_required:
        reviews = _require_list(evidence.get("reviews"), "reviews")
        latest = _effective_owner_review(reviews, owner)
        if latest is None:
            raise GuardError(
                "a non-owner pull request requires approval by the pinned owner identity"
            )
        if str(latest.get("state", "")).upper() != "APPROVED":
            raise GuardError("the pinned owner's effective review is not APPROVED")
        if latest.get("commit_id") != head_sha:
            raise GuardError(
                "owner approval is stale; it must apply to the current pull request head"
            )

    warnings: list[str] = []
    if owner.key_status.upper() != "ACTIVE" or not owner.key_fingerprints:
        warnings.append(
            "No active hardware-backed owner SSH signing fingerprint is pinned. "
            "Repository identity checks reduce impersonation risk but do not prove "
            "physical human identity or prevent account compromise."
        )

    return GuardDecision(
        owner_authored=owner_authored,
        protected_paths=protected_paths,
        owner_approval_required=owner_approval_required,
        governance_issues=governance_issues,
        owner_key_attested=owner_key_attested,
        warnings=tuple(warnings),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence",
        type=pathlib.Path,
        required=True,
        help="JSON evidence emitted by the GitHub Actions collection step",
    )
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=DEFAULT_MANIFEST,
        help="machine-readable owner identity manifest",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        owner = load_owner_identity(args.manifest)
        decision = evaluate(evidence, manifest, owner)
    except (OSError, json.JSONDecodeError, GuardError) as exc:
        print(f"FOUNDER_AUTHORITY_GUARD: FAIL: {exc}", file=sys.stderr)
        return 1

    print("FOUNDER_AUTHORITY_GUARD: PASS")
    print(f"owner_authored={str(decision.owner_authored).lower()}")
    print(
        "protected_paths="
        + (",".join(decision.protected_paths) if decision.protected_paths else "none")
    )
    print(
        "owner_approval_required="
        + str(decision.owner_approval_required).lower()
    )
    print(
        "governance_issues="
        + (
            ",".join(f"#{number}" for number in decision.governance_issues)
            if decision.governance_issues
            else "none"
        )
    )
    print(f"owner_key_attested={str(decision.owner_key_attested).lower()}")
    for warning in decision.warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
