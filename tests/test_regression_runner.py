"""
Regression suite for the run_scenario.py runner contract.

Covers gaps not addressed by test_run_scenario_cli.py:
  - Whitespace-only string rejection  (schema pattern constraint from PR #89)
  - Additional-properties rejection   (schema additionalProperties: false)
  - Invalid output path               (write-error handling from PR #90)
  - Byte-identical deterministic output
  - Output format contract             (trailing newline, sorted keys, UTF-8)
  - No-arguments edge case
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_SCENARIO = REPO_ROOT / "run_scenario.py"
EXAMPLE = REPO_ROOT / "example_scenario.json"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(RUN_SCENARIO), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


# ---------------------------------------------------------------------------
# Schema rejection: whitespace-only strings
# ---------------------------------------------------------------------------

class TestWhitespaceRejection:
    """Verify the pattern constraint rejects whitespace-only strings."""

    def test_whitespace_only_title_rejected(self) -> None:
        proc = _run_cli("--scenario", str(FIXTURES / "whitespace_title.json"))
        assert proc.returncode == 2
        assert "[schema-error]" in proc.stderr
        assert "title" in proc.stderr

    def test_whitespace_only_role_name_rejected(self, tmp_path: Path) -> None:
        scenario = {
            "title": "Valid",
            "description": "Valid",
            "roles": [{"name": "  ", "role": "mediator"}],
            "success_criteria": {"k": 1},
            "max_rounds": 3,
        }
        f = tmp_path / "ws_role.json"
        f.write_text(json.dumps(scenario), encoding="utf-8")
        proc = _run_cli("--scenario", str(f))
        assert proc.returncode == 2
        assert "[schema-error]" in proc.stderr

    def test_whitespace_only_description_rejected(self, tmp_path: Path) -> None:
        scenario = {
            "title": "Valid",
            "description": "\t\n ",
            "roles": [{"name": "A", "role": "r"}],
            "success_criteria": {"k": 1},
            "max_rounds": 3,
        }
        f = tmp_path / "ws_desc.json"
        f.write_text(json.dumps(scenario), encoding="utf-8")
        proc = _run_cli("--scenario", str(f))
        assert proc.returncode == 2
        assert "[schema-error]" in proc.stderr


# ---------------------------------------------------------------------------
# Schema rejection: additional properties
# ---------------------------------------------------------------------------

class TestAdditionalPropertiesRejection:
    """Verify additionalProperties: false blocks unknown keys."""

    def test_extra_top_level_field_rejected(self) -> None:
        proc = _run_cli("--scenario", str(FIXTURES / "extra_field.json"))
        assert proc.returncode == 2
        assert "[schema-error]" in proc.stderr
        assert "unexpected_field" in proc.stderr.lower() or "additional" in proc.stderr.lower()

    def test_extra_role_field_rejected(self, tmp_path: Path) -> None:
        scenario = {
            "title": "Valid",
            "description": "Valid",
            "roles": [{"name": "A", "role": "r", "bonus": True}],
            "success_criteria": {"k": 1},
            "max_rounds": 3,
        }
        f = tmp_path / "extra_role.json"
        f.write_text(json.dumps(scenario), encoding="utf-8")
        proc = _run_cli("--scenario", str(f))
        assert proc.returncode == 2
        assert "[schema-error]" in proc.stderr


# ---------------------------------------------------------------------------
# Input errors: write failures
# ---------------------------------------------------------------------------

class TestOutputWriteError:
    """Verify graceful handling when the output path is not writable."""

    def test_invalid_output_dir_returns_input_error(self, tmp_path: Path) -> None:
        bad_output = tmp_path / "no_such_dir" / "deep" / "out.json"
        proc = _run_cli(
            "--scenario", str(EXAMPLE),
            "--output", str(bad_output),
            "--seed", "42",
        )
        assert proc.returncode == 2
        assert "[input-error]" in proc.stderr
        assert "cannot write output file" in proc.stderr


# ---------------------------------------------------------------------------
# Input errors: no arguments
# ---------------------------------------------------------------------------

class TestNoArguments:
    """Verify the runner fails cleanly with no arguments."""

    def test_no_args_returns_error(self) -> None:
        proc = _run_cli()
        assert proc.returncode == 2
        assert "[input-error]" in proc.stderr


# ---------------------------------------------------------------------------
# Output format contract
# ---------------------------------------------------------------------------

class TestOutputFormatContract:
    """Verify the exact output format produced by the runner."""

    @pytest.fixture()
    def result_file(self, tmp_path: Path) -> Path:
        output = tmp_path / "result.json"
        proc = _run_cli(
            "--scenario", str(EXAMPLE),
            "--output", str(output),
            "--seed", "42",
        )
        assert proc.returncode == 0
        return output

    def test_output_has_trailing_newline(self, result_file: Path) -> None:
        raw = result_file.read_bytes()
        assert raw.endswith(b"\n")
        assert not raw.endswith(b"\n\n")  # exactly one trailing newline

    def test_output_is_valid_utf8(self, result_file: Path) -> None:
        raw = result_file.read_bytes()
        raw.decode("utf-8")  # raises UnicodeDecodeError if not valid

    def test_output_keys_are_sorted(self, result_file: Path) -> None:
        payload = json.loads(result_file.read_text(encoding="utf-8"))
        assert list(payload.keys()) == sorted(payload.keys())

    def test_output_file_is_byte_identical_across_runs(self, tmp_path: Path) -> None:
        out_a = tmp_path / "a.json"
        out_b = tmp_path / "b.json"

        proc_a = _run_cli(
            "--scenario", str(EXAMPLE),
            "--output", str(out_a),
            "--seed", "42",
        )
        proc_b = _run_cli(
            "--scenario", str(EXAMPLE),
            "--output", str(out_b),
            "--seed", "42",
        )
        assert proc_a.returncode == 0
        assert proc_b.returncode == 0
        assert out_a.read_bytes() == out_b.read_bytes()
