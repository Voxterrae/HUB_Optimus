from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RFC_DIR = REPO_ROOT / "docs" / "rfc"
REGISTRY_PATH = RFC_DIR / "registry.v1.json"


def _registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _is_optional_positive_int(value: object) -> bool:
    return value is None or (
        isinstance(value, int) and not isinstance(value, bool) and value > 0
    )


def test_registry_covers_every_rfc_markdown_once() -> None:
    registry = _registry()
    registered = [entry["path"] for entry in registry["rfcs"]]
    on_disk = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in RFC_DIR.glob("*.md")
        if path.name != "README.md"
    }

    assert len(registered) == len(set(registered))
    assert set(registered) == on_disk


def test_registry_has_versioned_evidence_and_decision_fields() -> None:
    registry = _registry()
    baseline = registry["baseline"]
    allowed_states = set(registry["lifecycle_states"])
    required_fields = {
        "id",
        "path",
        "title",
        "lifecycle",
        "proposal_issue",
        "record_pr",
        "decision_pr",
        "implementation_prs",
        "owner",
        "ratifier",
        "evidence_paths",
        "note",
    }

    assert registry["format_version"] == 1
    assert baseline["repository"] == "Voxterrae/HUB_Optimus"
    assert re.fullmatch(r"[0-9a-f]{40}", baseline["verified_commit"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", baseline["verified_at"])
    assert allowed_states == {
        "Proposed",
        "Draft",
        "Accepted",
        "Partially Implemented",
        "Implemented",
        "Superseded",
        "Rejected",
    }

    ids: set[str] = set()
    for entry in registry["rfcs"]:
        assert set(entry) == required_fields
        assert entry["id"] not in ids
        ids.add(entry["id"])
        assert entry["lifecycle"] in allowed_states
        assert _is_optional_positive_int(entry["proposal_issue"])
        assert _is_optional_positive_int(entry["record_pr"])
        assert _is_optional_positive_int(entry["decision_pr"])
        assert all(
            isinstance(number, int)
            and not isinstance(number, bool)
            and number > 0
            for number in entry["implementation_prs"]
        )
        assert entry["owner"] is None or isinstance(entry["owner"], str)
        assert entry["ratifier"] is None or isinstance(entry["ratifier"], str)
        assert entry["note"].strip()
        assert entry["evidence_paths"]
        for relative in entry["evidence_paths"]:
            assert (REPO_ROOT / relative).is_file(), relative

        if entry["lifecycle"] in {"Accepted", "Implemented"}:
            assert entry["decision_pr"] is not None
            assert entry["owner"]
            assert entry["ratifier"]
        if entry["lifecycle"] in {"Partially Implemented", "Implemented"}:
            assert entry["implementation_prs"]


def test_current_lifecycle_snapshot_is_explicitly_unratified() -> None:
    entries = _registry()["rfcs"]
    counts = {
        state: sum(1 for entry in entries if entry["lifecycle"] == state)
        for state in _registry()["lifecycle_states"]
    }
    url_intake = next(
        entry for entry in entries if entry["id"] == "operator-controlled-url-intake"
    )

    assert counts["Draft"] == 15
    assert counts["Partially Implemented"] == 1
    assert counts["Accepted"] == 0
    assert counts["Implemented"] == 0
    assert url_intake["decision_pr"] is None
    assert url_intake["implementation_prs"] == [1717, 1720]


def test_plain_overview_and_capability_ledger_keep_claim_classes_separate() -> None:
    overview = (REPO_ROOT / "docs/context/PROJECT_OVERVIEW.md").read_text(
        encoding="utf-8"
    )
    capabilities = (
        REPO_ROOT / "docs/architecture/capability_status.md"
    ).read_text(encoding="utf-8")

    for label in (
        "Verified fact",
        "Human/project declaration",
        "Calculation or synthetic observation",
        "Estimate or inference",
        "Proposal",
        "Unknown / unverified",
    ):
        assert label in overview

    assert "Kernel, consensus, runtime, and RFC are different things" in overview
    assert "| Multilingual documentation structure | Partial |" in capabilities
    assert "| Semantic Engine contracts and CLI | Prototype |" in capabilities
    assert "| Post-quantum control plane | Draft / RFC |" in capabilities
    assert (
        "| Public remote Semantic Engine or autonomous analysis | Not implemented |"
        in capabilities
    )
    assert "| `Voxterrae/HUB-Optimus-labs` artifacts | External / unresolved |" in (
        capabilities
    )
