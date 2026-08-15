from __future__ import annotations

import json
import pathlib

import pytest

from tools.founder_authority_guard import (
    GuardError,
    OwnerIdentity,
    collect_changed_paths,
    evaluate,
    extract_issue_numbers,
    load_owner_identity,
)

OWNER_IDENTITY = {"login": "Voxterrae", "id": 249308740}
WEB_FLOW_IDENTITY = {"login": "web-flow", "id": 19864447}
OWNER = OwnerIdentity(
    login="Voxterrae",
    user_id=249308740,
    key_status="PENDING_HARDWARE_BACKED_KEY_ENROLLMENT",
    key_fingerprints=(),
)
ACTIVE_OWNER = OwnerIdentity(
    login="Voxterrae",
    user_id=249308740,
    key_status="ACTIVE",
    key_fingerprints=("SHA256:owner-hardware-key",),
)

MANIFEST = {
    "constitutional_files": [
        "docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md",
        "config/governance/owner_identity.v1.json",
    ]
}


def verified_commit(
    sha: str = "a" * 40,
    *,
    author: dict[str, object] | None = None,
    committer: dict[str, object] | None = None,
    signature: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "sha": sha,
        "verification": {"verified": True, "reason": "valid"},
        "author": author or dict(OWNER_IDENTITY),
        "committer": committer or dict(OWNER_IDENTITY),
        "signature": signature,
    }


def valid_governance_issue(number: int = 1861) -> dict[str, object]:
    return {
        "number": number,
        "exists": True,
        "is_pull_request": False,
        "state": "open",
        "labels": ["documentation", "governance"],
        "author": dict(OWNER_IDENTITY),
    }


def evidence() -> dict[str, object]:
    return {
        "repository": {
            "full_name": "Voxterrae/HUB_Optimus",
            "owner": dict(OWNER_IDENTITY),
        },
        "pull_request": {
            "number": 1862,
            "author": dict(OWNER_IDENTITY),
            "body": "Related to #1861",
            "head_sha": "a" * 40,
            "head_ref": "agent/founder-owner-constitutional-lock",
            "base_ref": "main",
        },
        "changed_files": [
            "docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md"
        ],
        "governance_issues": [valid_governance_issue()],
        "reviews": [],
        "commits": [verified_commit()],
    }


def test_owner_can_author_protected_change() -> None:
    decision = evaluate(evidence(), MANIFEST, OWNER)
    assert decision.owner_authored is True
    assert decision.owner_approval_required is False
    assert decision.protected_paths
    assert decision.governance_issues == (1861,)
    assert decision.owner_key_attested is False
    assert decision.warnings


def test_same_login_wrong_immutable_id_is_rejected() -> None:
    payload = evidence()
    payload["pull_request"]["author"]["id"] = 999  # type: ignore[index]
    with pytest.raises(GuardError, match="only the pinned owner identity"):
        evaluate(payload, MANIFEST, OWNER)


def test_non_owner_cannot_author_protected_change() -> None:
    payload = evidence()
    payload["pull_request"]["author"] = {  # type: ignore[index]
        "login": "contributor",
        "id": 123,
    }
    with pytest.raises(GuardError, match="only the pinned owner identity"):
        evaluate(payload, MANIFEST, OWNER)


def test_owner_pr_rejects_non_owner_protected_commit() -> None:
    payload = evidence()
    payload["commits"] = [
        verified_commit(
            author={"login": "contributor", "id": 123},
            committer={"login": "contributor", "id": 123},
        )
    ]
    with pytest.raises(GuardError, match="every commit in a protected-path"):
        evaluate(payload, MANIFEST, OWNER)


def test_owner_commit_accepts_github_web_flow_committer() -> None:
    payload = evidence()
    payload["commits"] = [verified_commit(committer=dict(WEB_FLOW_IDENTITY))]
    decision = evaluate(payload, MANIFEST, OWNER)
    assert decision.owner_authored is True


def test_owner_commit_rejects_untrusted_committer() -> None:
    payload = evidence()
    payload["commits"] = [
        verified_commit(committer={"login": "github-actions[bot]", "id": 41898282})
    ]
    with pytest.raises(GuardError, match="owner-committed or committed by GitHub web-flow"):
        evaluate(payload, MANIFEST, OWNER)


def test_owner_protected_change_requires_issue_reference() -> None:
    payload = evidence()
    payload["pull_request"]["body"] = "No issue link"  # type: ignore[index]
    with pytest.raises(GuardError, match="Related to #N"):
        evaluate(payload, MANIFEST, OWNER)


def test_missing_governance_issue_is_rejected() -> None:
    payload = evidence()
    payload["governance_issues"] = [
        {
            "number": 1861,
            "exists": False,
            "is_pull_request": False,
            "labels": [],
            "author": None,
        }
    ]
    with pytest.raises(GuardError, match="#1861 does not exist"):
        evaluate(payload, MANIFEST, OWNER)


def test_pull_request_cannot_satisfy_governance_issue_link() -> None:
    payload = evidence()
    payload["governance_issues"][0]["is_pull_request"] = True  # type: ignore[index]
    with pytest.raises(GuardError, match="is a pull request"):
        evaluate(payload, MANIFEST, OWNER)


def test_governance_issue_must_be_owner_authored() -> None:
    payload = evidence()
    payload["governance_issues"][0]["author"] = {  # type: ignore[index]
        "login": "contributor",
        "id": 123,
    }
    with pytest.raises(GuardError, match="not owner-authored"):
        evaluate(payload, MANIFEST, OWNER)


def test_governance_issue_must_have_governance_label() -> None:
    payload = evidence()
    payload["governance_issues"][0]["labels"] = ["documentation"]  # type: ignore[index]
    with pytest.raises(GuardError, match="not labelled governance"):
        evaluate(payload, MANIFEST, OWNER)


def test_all_declared_governance_issue_references_are_validated() -> None:
    payload = evidence()
    payload["pull_request"]["body"] = (  # type: ignore[index]
        "Related to #1861\nGovernance issue #999999"
    )
    payload["governance_issues"].append(  # type: ignore[union-attr]
        {
            "number": 999999,
            "exists": False,
            "is_pull_request": False,
            "labels": [],
            "author": None,
        }
    )
    with pytest.raises(GuardError, match="#999999 does not exist"):
        evaluate(payload, MANIFEST, OWNER)


def test_non_owner_general_change_requires_current_owner_approval() -> None:
    payload = evidence()
    payload["changed_files"] = ["examples/example.json"]
    payload["pull_request"]["author"] = {  # type: ignore[index]
        "login": "contributor",
        "id": 123,
    }
    with pytest.raises(GuardError, match="requires approval"):
        evaluate(payload, MANIFEST, OWNER)


def test_non_owner_general_change_passes_with_current_owner_approval() -> None:
    payload = evidence()
    payload["changed_files"] = ["examples/example.json"]
    payload["pull_request"]["author"] = {  # type: ignore[index]
        "login": "contributor",
        "id": 123,
    }
    payload["reviews"] = [
        {
            "user": dict(OWNER_IDENTITY),
            "state": "APPROVED",
            "commit_id": "a" * 40,
        }
    ]
    decision = evaluate(payload, MANIFEST, OWNER)
    assert decision.owner_authored is False
    assert decision.owner_approval_required is True


def test_comment_only_review_does_not_revoke_current_approval() -> None:
    payload = evidence()
    payload["changed_files"] = ["examples/example.json"]
    payload["pull_request"]["author"] = {  # type: ignore[index]
        "login": "contributor",
        "id": 123,
    }
    payload["reviews"] = [
        {
            "user": dict(OWNER_IDENTITY),
            "state": "APPROVED",
            "commit_id": "a" * 40,
        },
        {
            "user": dict(OWNER_IDENTITY),
            "state": "COMMENTED",
            "commit_id": "a" * 40,
        },
    ]
    decision = evaluate(payload, MANIFEST, OWNER)
    assert decision.owner_approval_required is True


def test_changes_requested_after_approval_revokes_effective_approval() -> None:
    payload = evidence()
    payload["changed_files"] = ["examples/example.json"]
    payload["pull_request"]["author"] = {  # type: ignore[index]
        "login": "contributor",
        "id": 123,
    }
    payload["reviews"] = [
        {
            "user": dict(OWNER_IDENTITY),
            "state": "APPROVED",
            "commit_id": "a" * 40,
        },
        {
            "user": dict(OWNER_IDENTITY),
            "state": "CHANGES_REQUESTED",
            "commit_id": "a" * 40,
        },
    ]
    with pytest.raises(GuardError, match="effective review is not APPROVED"):
        evaluate(payload, MANIFEST, OWNER)


def test_stale_owner_approval_is_rejected() -> None:
    payload = evidence()
    payload["changed_files"] = ["examples/example.json"]
    payload["pull_request"]["author"] = {  # type: ignore[index]
        "login": "contributor",
        "id": 123,
    }
    payload["reviews"] = [
        {
            "user": dict(OWNER_IDENTITY),
            "state": "APPROVED",
            "commit_id": "b" * 40,
        }
    ]
    with pytest.raises(GuardError, match="approval is stale"):
        evaluate(payload, MANIFEST, OWNER)


def test_unverified_commit_is_rejected() -> None:
    payload = evidence()
    payload["commits"] = [
        {
            "sha": "a" * 40,
            "verification": {"verified": False, "reason": "unsigned"},
            "author": dict(OWNER_IDENTITY),
            "committer": dict(OWNER_IDENTITY),
            "signature": None,
        }
    ]
    with pytest.raises(GuardError, match="all commits must be verified"):
        evaluate(payload, MANIFEST, OWNER)


def test_active_owner_ssh_fingerprint_is_required_and_accepted() -> None:
    payload = evidence()
    payload["commits"] = [
        verified_commit(
            signature={
                "type": "SshSignature",
                "is_valid": True,
                "was_signed_by_github": False,
                "signer": dict(OWNER_IDENTITY),
                "key_fingerprint": "SHA256:owner-hardware-key",
            }
        )
    ]
    decision = evaluate(payload, MANIFEST, ACTIVE_OWNER)
    assert decision.owner_key_attested is True
    assert not decision.warnings


def test_active_owner_key_rejects_unpinned_fingerprint() -> None:
    payload = evidence()
    payload["commits"] = [
        verified_commit(
            signature={
                "type": "SshSignature",
                "is_valid": True,
                "was_signed_by_github": False,
                "signer": dict(OWNER_IDENTITY),
                "key_fingerprint": "SHA256:other-key",
            }
        )
    ]
    with pytest.raises(GuardError, match="unrecognized SSH fingerprint"):
        evaluate(payload, MANIFEST, ACTIVE_OWNER)


def test_active_owner_key_rejects_github_signed_commit() -> None:
    payload = evidence()
    payload["commits"] = [
        verified_commit(
            signature={
                "type": "SshSignature",
                "is_valid": True,
                "was_signed_by_github": True,
                "signer": dict(OWNER_IDENTITY),
                "key_fingerprint": "SHA256:owner-hardware-key",
            }
        )
    ]
    with pytest.raises(GuardError, match="signed by GitHub"):
        evaluate(payload, MANIFEST, ACTIVE_OWNER)


def test_active_owner_key_rejects_non_ssh_signature() -> None:
    payload = evidence()
    payload["commits"] = [
        verified_commit(
            signature={
                "type": "GpgSignature",
                "is_valid": True,
                "was_signed_by_github": False,
                "signer": dict(OWNER_IDENTITY),
                "key_id": "DEADBEEF",
            }
        )
    ]
    with pytest.raises(GuardError, match="requires SSH signatures"):
        evaluate(payload, MANIFEST, ACTIVE_OWNER)


def test_active_owner_key_requires_pinned_fingerprint() -> None:
    payload = evidence()
    owner = OwnerIdentity(
        login="Voxterrae",
        user_id=249308740,
        key_status="ACTIVE",
        key_fingerprints=(),
    )
    with pytest.raises(GuardError, match="no fingerprints are pinned"):
        evaluate(payload, MANIFEST, owner)


def test_wrong_repository_owner_is_rejected() -> None:
    payload = evidence()
    payload["repository"]["owner"] = {  # type: ignore[index]
        "login": "Voxterrae",
        "id": 999,
    }
    with pytest.raises(GuardError, match="repository owner identity"):
        evaluate(payload, MANIFEST, OWNER)


def test_manifest_loader_rejects_invalid_identity(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "owner.json"
    path.write_text(
        json.dumps(
            {
                "repository_identity": {
                    "login": "Voxterrae",
                    "immutable_user_id": 0,
                },
                "cryptographic_owner_keys": {
                    "status": "PENDING",
                    "fingerprints": [],
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(GuardError, match="positive integer"):
        load_owner_identity(path)


def test_manifest_loader_rejects_duplicate_fingerprint(
    tmp_path: pathlib.Path,
) -> None:
    path = tmp_path / "owner.json"
    path.write_text(
        json.dumps(
            {
                "repository_identity": {
                    "login": "Voxterrae",
                    "immutable_user_id": 249308740,
                },
                "cryptographic_owner_keys": {
                    "status": "ACTIVE",
                    "fingerprints": ["SHA256:key", "SHA256:key"],
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(GuardError, match="duplicate owner key fingerprint"):
        load_owner_identity(path)


def test_paths_with_parent_segments_fail_closed() -> None:
    payload = evidence()
    payload["changed_files"] = ["docs/../README.md"]
    with pytest.raises(GuardError, match="unsafe changed file path"):
        evaluate(payload, MANIFEST, OWNER)


def test_collect_changed_paths_includes_protected_previous_filename() -> None:
    paths = collect_changed_paths(
        [
            {
                "filename": "docs/archive/old-authority.md",
                "previous_filename": "docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md",
            }
        ]
    )
    assert paths == (
        "docs/archive/old-authority.md",
        "docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md",
    )


def test_collect_changed_paths_deduplicates_current_and_previous_paths() -> None:
    paths = collect_changed_paths(
        [
            {"filename": "README.md", "previous_filename": "README.md"},
            {"filename": "README.md"},
        ]
    )
    assert paths == ("README.md",)


def test_extract_issue_numbers_deduplicates_preserving_order() -> None:
    assert extract_issue_numbers(
        "Related to #1861\nGovernance issue #1881\nRelated to #1861"
    ) == (1861, 1881)
