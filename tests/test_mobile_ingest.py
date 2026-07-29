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
        pytest.skip("POSIX mode assertions require a POSIX platform")
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


def test_new_custom_file_is_private_but_existing_custom_mode_is_preserved(
    tmp_path: Path,
) -> None:
    if os.name != "posix":
        pytest.skip("POSIX mode assertions require a POSIX platform")
    mobile_ingest = _load_tool()
    new_output = tmp_path / "new-custom.jsonl"

    mobile_ingest._append_record(
        new_output,
        mobile_ingest._build_record("synthetic new custom claim", "argv"),
        protect_default_directory=False,
    )

    assert stat.S_IMODE(new_output.stat().st_mode) == 0o600

    existing_output = tmp_path / "existing-custom.jsonl"
    existing_output.write_text('{"existing": true}\n', encoding="utf-8")
    existing_output.chmod(0o640)

    mobile_ingest._append_record(
        existing_output,
        mobile_ingest._build_record("synthetic existing custom claim", "argv"),
        protect_default_directory=False,
    )

    assert stat.S_IMODE(existing_output.stat().st_mode) == 0o640


def test_existing_default_file_is_restricted_to_private_mode(
    tmp_path: Path,
    monkeypatch,
) -> None:
    if os.name != "posix":
        pytest.skip("POSIX mode assertions require a POSIX platform")
    mobile_ingest = _load_tool()
    repo_root = tmp_path / "repo"
    output = repo_root / ".local" / "intake" / "mobile_ingest.jsonl"
    output.parent.mkdir(parents=True)
    output.write_text('{"existing": true}\n', encoding="utf-8")
    output.chmod(0o640)
    monkeypatch.setattr(mobile_ingest, "REPO_ROOT", repo_root)

    mobile_ingest._append_record(
        output,
        mobile_ingest._build_record("synthetic default claim", "argv"),
        protect_default_directory=True,
    )

    assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_append_restores_missing_lf_jsonl_boundary(tmp_path: Path) -> None:
    mobile_ingest = _load_tool()
    output = tmp_path / "intake.jsonl"
    output.write_bytes(b'{"existing":true}')

    mobile_ingest._append_record(
        output,
        mobile_ingest._build_record("synthetic boundary claim", "argv"),
        protect_default_directory=False,
    )

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"existing": True}
    assert json.loads(lines[1])["claim"] == "synthetic boundary claim"
    assert output.read_bytes().endswith(b"\n")


def test_option_like_claim_is_stored_without_parser_echo(tmp_path: Path) -> None:
    output = tmp_path / "intake.jsonl"
    option_like_claim = "--synthetic-private-claim"

    result = _run_tool("--output", str(output), option_like_claim)

    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["claim"] == option_like_claim
    assert option_like_claim not in result.stdout
    assert option_like_claim not in result.stderr


def test_runtime_error_uses_controlled_non_echo_failure(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    mobile_ingest = _load_tool()
    claim = "synthetic runtime failure claim"

    def fail_append(*args, **kwargs):
        raise RuntimeError("cyclic path resolution")

    monkeypatch.setattr(mobile_ingest, "_append_record", fail_append)

    result = mobile_ingest.main(["--output", str(tmp_path / "out.jsonl"), claim])
    captured = capsys.readouterr()

    assert result == 1
    assert "[mobile_ingest:error] cyclic path resolution" in captured.err
    assert claim not in captured.err
    assert claim not in captured.out
    assert "Traceback" not in captured.err


def test_default_private_directory_cannot_escape_through_symlink(
    tmp_path: Path,
    monkeypatch,
) -> None:
    if os.name != "posix":
        pytest.skip("symlink boundary assertions require a POSIX platform")
    mobile_ingest = _load_tool()
    repo_root = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo_root.mkdir()
    outside.mkdir()
    (repo_root / ".local").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(mobile_ingest, "REPO_ROOT", repo_root)
    output = repo_root / ".local" / "intake" / "mobile_ingest.jsonl"

    with pytest.raises(OSError):
        mobile_ingest._append_record(
            output,
            mobile_ingest._build_record("synthetic symlink claim", "argv"),
            protect_default_directory=True,
        )

    assert not (outside / "intake").exists()


def test_cyclic_default_symlink_fails_without_traceback(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    if os.name != "posix":
        pytest.skip("symlink boundary assertions require a POSIX platform")
    mobile_ingest = _load_tool()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".local").symlink_to(".local", target_is_directory=True)
    output = repo_root / ".local" / "intake" / "mobile_ingest.jsonl"
    monkeypatch.setattr(mobile_ingest, "REPO_ROOT", repo_root)
    monkeypatch.setattr(mobile_ingest, "DEFAULT_OUTPUT_PATH", output)
    claim = "synthetic cyclic symlink claim"

    result = mobile_ingest.main([claim])
    captured = capsys.readouterr()

    assert result == 1
    assert "[mobile_ingest:error]" in captured.err
    assert claim not in captured.err
    assert claim not in captured.out
    assert "Traceback" not in captured.err


def test_default_writer_fails_closed_without_secure_descriptor_support(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mobile_ingest = _load_tool()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output = repo_root / ".local" / "intake" / "mobile_ingest.jsonl"
    monkeypatch.setattr(mobile_ingest, "REPO_ROOT", repo_root)
    monkeypatch.setattr(
        mobile_ingest,
        "_supports_secure_default_writer",
        lambda: False,
    )

    with pytest.raises(OSError, match="fail|requires POSIX"):
        mobile_ingest._append_record(
            output,
            mobile_ingest._build_record("synthetic unsupported claim", "argv"),
            protect_default_directory=True,
        )

    assert not output.exists()


def test_default_parent_replacement_cannot_redirect_descriptor_write(
    tmp_path: Path,
    monkeypatch,
) -> None:
    if os.name != "posix":
        pytest.skip("descriptor race assertion requires a POSIX platform")
    mobile_ingest = _load_tool()
    if not mobile_ingest._supports_secure_default_writer():
        pytest.skip("secure directory descriptors are unavailable")

    repo_root = tmp_path / "repo"
    intake_directory = repo_root / ".local" / "intake"
    moved_directory = repo_root / ".local" / "intake-original"
    outside = tmp_path / "outside"
    intake_directory.mkdir(parents=True)
    outside.mkdir()
    output = intake_directory / "mobile_ingest.jsonl"
    monkeypatch.setattr(mobile_ingest, "REPO_ROOT", repo_root)

    real_open = os.open
    parent_replaced = False

    def racing_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal parent_replaced
        if (
            path == output.name
            and dir_fd is not None
            and not parent_replaced
        ):
            intake_directory.rename(moved_directory)
            intake_directory.symlink_to(outside, target_is_directory=True)
            parent_replaced = True
        if dir_fd is None:
            return real_open(path, flags, mode)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(mobile_ingest.os, "open", racing_open)
    monkeypatch.setattr(
        mobile_ingest,
        "_supports_secure_default_writer",
        lambda: True,
    )

    mobile_ingest._append_record(
        output,
        mobile_ingest._build_record("synthetic race claim", "argv"),
        protect_default_directory=True,
    )

    assert parent_replaced
    assert not (outside / output.name).exists()
    stored = json.loads(
        (moved_directory / output.name).read_text(encoding="utf-8")
    )
    assert stored["claim"] == "synthetic race claim"
