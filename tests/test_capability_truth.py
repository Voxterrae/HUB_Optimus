from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = (
    REPO_ROOT / "docs" / "architecture" / "capability_evidence.v1.json"
)
CAPABILITY_PATH = REPO_ROOT / "docs" / "architecture" / "capability_status.md"
CHECKPOINT_PATH = REPO_ROOT / "docs" / "context" / "hub_optimus_checkpoint.md"


def _evidence() -> dict:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def test_capability_evidence_has_an_explicit_offline_baseline() -> None:
    evidence = _evidence()
    baseline = evidence["baseline"]

    assert evidence["format_version"] == 1
    assert baseline["repository"] == "Voxterrae/HUB_Optimus"
    assert baseline["kind"] == "repository-tree"
    assert re.fullmatch(r"[0-9a-f]{40}", baseline["commit"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", baseline["verified_at"])

    capability_text = CAPABILITY_PATH.read_text(encoding="utf-8")
    assert baseline["commit"] in capability_text
    assert baseline["verified_at"] in capability_text

    for relative in evidence["current_truth_documents"]:
        assert (REPO_ROOT / relative).is_file(), relative
    for command in evidence["verification_commands"]:
        assert command["purpose"].strip()
        assert command["command"].strip()


def test_terminal_pull_requests_are_not_called_drafts_in_current_truth_docs() -> None:
    evidence = _evidence()
    terminal = {
        record["number"]: record for record in evidence["terminal_pull_requests"]
    }

    assert len(terminal) == len(evidence["terminal_pull_requests"])
    for number, record in terminal.items():
        assert record["state"] in {"merged", "closed-unmerged"}
        if record["state"] == "merged":
            assert re.fullmatch(r"[0-9a-f]{40}", record["commit"])
        else:
            assert record["commit"] is None

    stale: list[str] = []
    for relative in evidence["current_truth_documents"]:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not re.search(r"\b(?:drafts?|open)\b", line, flags=re.IGNORECASE):
                continue
            numbers = {int(value) for value in re.findall(r"#(\d+)", line)}
            for number in sorted(numbers & terminal.keys()):
                stale.append(f"{relative}:{line_number}: PR #{number}")

    assert stale == []


def test_every_checkpoint_document_is_machine_classified_as_historical() -> None:
    evidence = _evidence()
    checkpoint_records = {
        record["path"]: record for record in evidence["archived_documents"]
    }
    checkpoint_files = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "docs" / "context").rglob("*.md")
        if "checkpoint" in path.name.casefold()
    }

    assert checkpoint_files == set(checkpoint_records)
    assert CHECKPOINT_PATH.relative_to(REPO_ROOT).as_posix() in checkpoint_files

    for relative in checkpoint_files:
        record = checkpoint_records[relative]
        assert record["status"] == "historical"
        assert record["current"] is False
        assert record["superseded_by"] == [
            "docs/context/SOURCE_OF_TRUTH.md",
            "docs/context/STATUS.md",
            "docs/context/AI_HANDOFF.md",
            "docs/architecture/capability_status.md",
        ]

        checkpoint = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "Status: **historical snapshot (non-authoritative)**" in checkpoint
        assert "Single source of truth for the operational state" not in checkpoint
        assert "Updated at each significant milestone" not in checkpoint
        assert "## Current phase" not in checkpoint
        assert "## Next task" not in checkpoint
        assert "docs/context/SOURCE_OF_TRUTH.md" in checkpoint
