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


def test_example_scenario_happy_path() -> None:
    assert EXAMPLE.exists()
    proc = _run_cli("--scenario", str(EXAMPLE), "--seed", "42")
    assert proc.returncode == 0

    payload = json.loads(proc.stdout)
    assert payload["status"] in {"success", "failure"}
    assert isinstance(payload["rounds"], int)
    assert isinstance(payload["history"], list)
    assert isinstance(payload["detail"], str)


@pytest.mark.parametrize(
    ("payload", "expected_fragment"),
    [
        (
            {
                "title": "missing max_rounds",
                "description": "invalid scenario",
                "roles": [{"name": "A", "role": "Mediator"}],
                "success_criteria": {"criterion": "ok"},
            },
            "max_rounds",
        ),
        (
            {
                "title": "empty roles",
                "description": "invalid scenario",
                "roles": [],
                "success_criteria": {"criterion": "ok"},
                "max_rounds": 2,
            },
            ".roles",
        ),
        (
            {
                "title": "extra field",
                "description": "invalid scenario",
                "roles": [{"name": "A", "role": "Mediator"}],
                "success_criteria": {"criterion": "ok"},
                "max_rounds": 2,
                "unexpected": True,
            },
            "Additional properties",
        ),
    ],
)
def test_invalid_schema_fails_fast_with_stable_exit_code(
    tmp_path: Path, payload: dict[str, object], expected_fragment: str
) -> None:
    invalid = tmp_path / "invalid_scenario.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")

    proc = _run_cli("--scenario", str(invalid))
    assert proc.returncode == 2
    assert "[schema-error]" in proc.stderr
    assert "scenario.schema.json" in proc.stderr
    assert expected_fragment in proc.stderr


def test_missing_file_returns_input_error_code() -> None:
    missing = REPO_ROOT / "does_not_exist_scenario.json"
    proc = _run_cli("--scenario", str(missing))
    assert proc.returncode == 2
    assert "[input-error]" in proc.stderr
    assert "Scenario file not found" in proc.stderr


def test_invalid_json_returns_schema_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"title": "oops", "roles": [}', encoding="utf-8")
    proc = _run_cli("--scenario", str(bad))
    assert proc.returncode == 2
    assert "[schema-error]" in proc.stderr
    assert "Invalid JSON" in proc.stderr
