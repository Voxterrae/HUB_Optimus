#!/usr/bin/env python3
"""Fail-closed governance guard for HUB_Optimus owner authority.

The guard does not prove a human's legal identity and cannot prevent account
compromise. It enforces the repository evidence that can be checked safely:

- immutable GitHub login and numeric user ID;
- protected-path authorship by the owner repository identity;
- verified commits;
- explicit issue linkage for constitutional changes;
- owner approval at the current head for non-owner contribution PRs.

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


def _latest_owner_review(
    reviews: list[Any], owner: OwnerIdentity
) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for raw in reviews:
        review = _require_mapping(raw, "review")
        user = review.get("user")
        if not isinstance(user, dict) or not identity_matches(user, owner):
            continue
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
    if protected_paths and not owner_authored:
        raise GuardError(
            "only the pinned owner identity may author constitutional/control-plane "
            "changes; protected paths: " + ", ".join(protected_paths)
        )

    if protected_paths and ISSUE_REFERENCE_RE.search(body) is None:
        raise GuardError(
            "constitutional/control-plane changes require an explicit 'Related to #N' "
            "or 'Governance issue #N' reference in the pull request body"
        )

    owner_approval_required = not owner_authored
    if owner_approval_required:
        reviews = _require_list(evidence.get("reviews"), "reviews")
        latest = _latest_owner_review(reviews, owner)
        if latest is None:
            raise GuardError(
                "a non-owner pull request requires approval by the pinned owner identity"
            )
        if str(latest.get("state", "")).upper() != "APPROVED":
            raise GuardError("the pinned owner's latest review is not APPROVED")
        if latest.get("commit_id") != head_sha:
            raise GuardError(
                "owner approval is stale; it must apply to the current pull request head"
            )

    warnings: list[str] = []
    if owner.key_status != "ACTIVE" or not owner.key_fingerprints:
        warnings.append(
            "No active hardware-backed owner signing fingerprint is pinned. "
            "Repository identity checks reduce impersonation risk but do not prove "
            "physical human identity or prevent account compromise."
        )

    return GuardDecision(
        owner_authored=owner_authored,
        protected_paths=protected_paths,
        owner_approval_required=owner_approval_required,
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
    for warning in decision.warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
