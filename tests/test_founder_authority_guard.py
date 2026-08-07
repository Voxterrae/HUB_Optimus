from __future__ import annotations

import copy
import json
import pathlib

import pytest

from tools.founder_authority_guard import (
    GuardError,
    OwnerIdentity,
    evaluate,
    load_owner_identity,
)

OWNER = OwnerIdentity(
    login="Voxterrae",
    user_id=249308740,
    key_status="PENDING_HARDWARE_BACKED_KEY_ENROLLMENT",
    key_fingerprints=(),
)

MANIFEST = {
    "constitutional_files": [
        "docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md",
        "config/governance/owner_identity.v1.json",
    ]
}


def verified_commit(sha: str = "a" * 40) -> dict[str, object]:
    return {
        "sha": sha,
        "verification": {"verified": True, "reason": "valid"},
    }


def evidence() -> dict[str, object]:
    return {
        "repository": {
            "full_name": "Voxterrae/HUB_Optimus",
            "owner": {"login": "Voxterrae", "id": 249308740},
        },
        "pull_request": {
            "number": 1862,
            "author": {"login": "Voxterrae", "id": 249308740},
            "body": "Related to #1861",
            "head_sha": "a" * 40,
            "head_ref": "agent/founder-owner-constitutional-lock",
            "base_ref": "main",
        },
        "changed_files": [
            "docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md"
        ],
        "reviews": [],
        "commits": [verified_commit()],
    }


def test_owner_can_author_protected_change() -> None:
    decision = evaluate(evidence(), MANIFEST, OWNER)
    assert decision.owner_authored is True
    assert decision.owner_approval_required is False
    assert decision.protected_paths
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


def test_owner_protected_change_requires_issue_reference() -> None:
    payload = evidence()
    payload["pull_request"]["body"] = "No issue link"  # type: ignore[index]
    with pytest.raises(GuardError, match="Related to #N"):
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
            "user": {"login": "Voxterrae", "id": 249308740},
            "state": "APPROVED",
            "commit_id": "a" * 40,
        }
    ]
    decision = evaluate(payload, MANIFEST, OWNER)
    assert decision.owner_authored is False
    assert decision.owner_approval_required is True


def test_stale_owner_approval_is_rejected() -> None:
    payload = evidence()
    payload["changed_files"] = ["examples/example.json"]
    payload["pull_request"]["author"] = {  # type: ignore[index]
        "login": "contributor",
        "id": 123,
    }
    payload["reviews"] = [
        {
            "user": {"login": "Voxterrae", "id": 249308740},
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
        }
    ]
    with pytest.raises(GuardError, match="all commits must be verified"):
        evaluate(payload, MANIFEST, OWNER)


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


def test_paths_with_parent_segments_fail_closed() -> None:
    payload = evidence()
    payload["changed_files"] = ["docs/../README.md"]
    with pytest.raises(GuardError, match="unsafe changed file path"):
        evaluate(payload, MANIFEST, OWNER)
