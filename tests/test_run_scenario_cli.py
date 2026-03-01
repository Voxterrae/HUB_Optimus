from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_SCENARIO = REPO_ROOT / "run_scenario.py"
EXAMPLE = REPO_ROOT / "example_scenario.json"
SCHEMA_PATH = REPO_ROOT / "scenario.schema.json"


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


def test_example_scenario_happy_path(tmp_path: Path) -> None:
    assert EXAMPLE.exists()
    output_path = tmp_path / "scenario_result.json"
    proc = _run_cli(
        "--scenario",
        str(EXAMPLE),
        "--output",
        str(output_path),
        "--seed",
        "42",
    )
    assert proc.returncode == 0

    assert output_path.is_file()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] in {"success", "failure"}
    assert isinstance(payload["rounds"], int)
    assert isinstance(payload["history"], list)
    assert isinstance(payload["detail"], str)


def test_cli_output_is_deterministic(tmp_path: Path) -> None:
    assert EXAMPLE.exists()
    output_a = tmp_path / "scenario_output_a.json"
    output_b = tmp_path / "scenario_output_b.json"

    proc_a = _run_cli(
        "--scenario",
        str(EXAMPLE),
        "--output",
        str(output_a),
        "--seed",
        "42",
    )
    proc_b = _run_cli(
        "--scenario",
        str(EXAMPLE),
        "--output",
        str(output_b),
        "--seed",
        "42",
    )

    assert proc_a.returncode == 0
    assert proc_b.returncode == 0
    assert output_a.is_file()
    assert output_b.is_file()

    payload_a = json.loads(output_a.read_text(encoding="utf-8"))
    payload_b = json.loads(output_b.read_text(encoding="utf-8"))
    assert payload_a == payload_b


def test_invalid_schema_fails_fast_with_stable_exit_code(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid_scenario.json"
    invalid.write_text(
        json.dumps(
            {
                "title": "bad scenario",
                "description": "missing required constraints",
                "roles": [],
                "success_criteria": {},
                "max_rounds": 0,
            }
        ),
        encoding="utf-8",
    )

    proc = _run_cli("--scenario", str(invalid))
    assert proc.returncode == 2
    assert "[schema-error]" in proc.stderr
    assert "roles" in proc.stderr
    assert "success_criteria" in proc.stderr
    assert "max_rounds" in proc.stderr


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


def test_schema_file_defines_required_contract() -> None:
    """Coupling guard: fails if scenario.schema.json changes the expected validation contract.

    This test ensures run_scenario.py stays in sync with scenario.schema.json.
    If the schema loosens or tightens required fields/constraints, this test
    will fail — prompting a conscious update to the validation logic.
    """
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    required = set(schema.get("required", []))
    assert required == {"title", "description", "roles", "success_criteria", "max_rounds"}, (
        "scenario.schema.json required fields changed — review run_scenario.py "
        "and update this test if the contract change is intentional"
    )
    props = schema.get("properties", {})
    assert props["roles"].get("minItems", 0) >= 1, (
        "schema must require at least 1 role (roles.minItems >= 1)"
    )
    assert props["success_criteria"].get("minProperties", 0) >= 1, (
        "schema must require at least 1 success criterion (success_criteria.minProperties >= 1)"
    )
    assert props["max_rounds"].get("minimum", 0) >= 1, (
        "schema must require max_rounds >= 1 (max_rounds.minimum >= 1)"
    )
