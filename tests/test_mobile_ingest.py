"""Tests for private, local-only mobile intake."""
from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "mobile_ingest.py"


def _load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mobile_ingest", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_tool(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=REPO_ROOT,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_explicit_output_writes_stable_private_raw_record(tmp_path: Path) -> None:
    output = tmp_path / "private" / "intake.jsonl"

    result = _run_tool("--output", str(output), "synthetic", "test", "claim")

    assert result.returncode == 0, result.stderr
    assert "Raw intake is unverified" in result.stderr
    assert "operator-managed" in result.stderr
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["schema_version"] == 1
    assert record["intake_id"].startswith("mobile-")
    assert record["source"] == {
        "channel": "mobile_termux",
        "input_method": "argv",
        "tool": "tools/mobile_ingest.py",
    }
    assert record["classification"] == "private_raw_intake"
    assert record["verification_status"] == "unverified"
    assert record["publication_status"] == "local_only"
    assert record["claim"] == "synthetic test claim"
    assert "synthetic test claim" not in result.stderr
    assert "synthetic test claim" not in result.stdout


def test_stdin_provenance_is_recorded(tmp_path: Path) -> None:
    output = tmp_path / "intake.jsonl"

    result = _run_tool("--output", str(output), stdin="synthetic stdin claim\n")

    assert result.returncode == 0, result.stderr
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["source"]["input_method"] == "stdin"
    assert record["claim"] == "synthetic stdin claim"


def test_empty_input_is_controlled(tmp_path: Path) -> None:
    output = tmp_path / "intake.jsonl"

    result = _run_tool("--output", str(output), stdin="")

    assert result.returncode == 1
    assert "[mobile_ingest:error] no input provided" in result.stderr
    assert "Traceback" not in result.stderr
    assert not output.exists()


def test_write_failure_is_controlled(tmp_path: Path) -> None:
    parent_file = tmp_path / "not-a-directory"
    parent_file.write_text("fixture", encoding="utf-8")

    result = _run_tool(
        "--output",
        str(parent_file / "intake.jsonl"),
        "synthetic",
        "claim",
    )

    assert result.returncode == 1
    assert "[mobile_ingest:error]" in result.stderr
    assert "Traceback" not in result.stderr


def test_default_path_is_repository_ignored() -> None:
    mobile_ingest = _load_tool()
    relative_path = mobile_ingest.DEFAULT_OUTPUT_PATH.relative_to(REPO_ROOT)
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", str(relative_path)],
        cwd=REPO_ROOT,
        check=False,
    )

    assert relative_path == Path(".local/intake/mobile_ingest.jsonl")
    assert result.returncode == 0


def test_private_writer_sets_posix_permissions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    if os.name != "posix":
        return
    mobile_ingest = _load_tool()
    monkeypatch.setattr(mobile_ingest, "REPO_ROOT", tmp_path)
    output = tmp_path / ".local" / "intake" / "mobile_ingest.jsonl"

    mobile_ingest._append_record(
        output,
        mobile_ingest._build_record("synthetic permissions claim", "argv"),
        protect_default_directory=True,
    )

    assert stat.S_IMODE(output.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_default_private_directory_cannot_escape_through_symlink(
    tmp_path: Path,
    monkeypatch,
) -> None:
    if os.name != "posix":
        return
    mobile_ingest = _load_tool()
    repo_root = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo_root.mkdir()
    outside.mkdir()
    (repo_root / ".local").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(mobile_ingest, "REPO_ROOT", repo_root)
    output = repo_root / ".local" / "intake" / "mobile_ingest.jsonl"

    with pytest.raises(OSError, match="resolves outside"):
        mobile_ingest._append_record(
            output,
            mobile_ingest._build_record("synthetic symlink claim", "argv"),
            protect_default_directory=True,
        )

    assert not (outside / "intake").exists()
