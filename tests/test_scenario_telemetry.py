"""Regression tests for controlled scenario telemetry outcomes."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = REPO_ROOT / "tools" / "scenario_telemetry.py"


def _load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("scenario_telemetry", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_scenario() -> dict[str, object]:
    return {
        "title": "Telemetry fixture",
        "description": "A valid scenario used to exercise the collector.",
        "roles": [{"name": "Alpha", "role": "negotiator"}],
        "success_criteria": {"offer": 5},
        "max_rounds": 1,
    }


def _run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_standard_json_constants_are_parse_outcomes(
    tmp_path: Path,
    constant: str,
) -> None:
    telemetry = _load_tool()
    path = tmp_path / "non-standard.json"
    source = json.dumps(_valid_scenario()).replace(
        '"offer": 5',
        f'"offer": {constant}',
    )
    path.write_text(source, encoding="utf-8")

    record = telemetry.collect_one(path, 42)

    assert record["processing_outcome"] == "parse_error"
    assert record["error_code"] == "invalid_json"
    assert record["schema_valid"] is False
    assert record["runtime_error"] is False


def test_non_object_json_is_a_parse_outcome(tmp_path: Path) -> None:
    telemetry = _load_tool()
    path = tmp_path / "array.json"
    path.write_text("[]\n", encoding="utf-8")

    record = telemetry.collect_one(path, 42)

    assert record["processing_outcome"] == "parse_error"
    assert record["error_code"] == "json_root_not_object"
    assert record["runtime_error"] is False


def test_invalid_utf8_is_a_parse_outcome(tmp_path: Path) -> None:
    telemetry = _load_tool()
    path = tmp_path / "invalid-utf8.json"
    path.write_bytes(b"\xff\xfe")

    record = telemetry.collect_one(path, 42)

    assert record["processing_outcome"] == "parse_error"
    assert record["error_code"] == "invalid_utf8"
    assert record["runtime_error"] is False


def test_duplicate_actor_names_are_a_schema_outcome(tmp_path: Path) -> None:
    telemetry = _load_tool()
    path = tmp_path / "duplicate-actors.json"
    payload = _valid_scenario()
    payload["roles"] = [
        {"name": "Alpha", "role": "negotiator"},
        {"name": "Alpha", "role": "mediator"},
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")

    record = telemetry.collect_one(path, 42)

    assert record["processing_outcome"] == "schema_error"
    assert record["error_code"] == "schema_invalid"
    assert record["schema_valid"] is False
    assert record["runtime_error"] is False


def test_missing_required_fields_are_a_schema_outcome(tmp_path: Path) -> None:
    telemetry = _load_tool()
    path = tmp_path / "missing-fields.json"
    path.write_text('{"title": "Incomplete"}\n', encoding="utf-8")

    record = telemetry.collect_one(path, 42)

    assert record["processing_outcome"] == "schema_error"
    assert record["error_code"] == "schema_invalid"
    assert record["schema_valid"] is False
    assert record["runtime_error"] is False


def test_wrong_field_types_are_a_schema_outcome(tmp_path: Path) -> None:
    telemetry = _load_tool()
    path = tmp_path / "wrong-types.json"
    path.write_text(
        json.dumps(
            {
                "title": "Wrong field types",
                "description": "The roles value must be an array.",
                "roles": 7,
                "success_criteria": {"offer": 5},
                "max_rounds": 1,
            }
        ),
        encoding="utf-8",
    )

    record = telemetry.collect_one(path, 42)

    assert record["processing_outcome"] == "schema_error"
    assert record["error_code"] == "schema_invalid"
    assert record["runtime_error"] is False


def test_index_outcomes_are_disjoint_and_non_negative() -> None:
    telemetry = _load_tool()
    outcomes = (
        "agreement",
        "no_agreement",
        "parse_error",
        "schema_error",
        "runtime_error",
    )
    records = [
        {
            "processing_outcome": outcome,
            "convergence_round": 2 if outcome == "agreement" else None,
            "family": "fixture",
        }
        for outcome in outcomes
    ]

    index = telemetry.build_index(records)

    assert index["total"] == 5
    assert index["passed_runtime"] == 2
    assert index["parse_failures"] == 1
    assert index["schema_invalid"] == 1
    assert index["runtime_failures"] == 1
    assert all(count >= 0 for count in index["processing_outcomes"].values())
    assert sum(index["processing_outcomes"].values()) == index["total"]
    assert index["agreements"] + index["no_agreements"] == index["passed_runtime"]


def test_cli_continues_after_bad_file_and_returns_partial_status(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "inputs"
    output_dir = tmp_path / "output"
    scenario_dir.mkdir()
    (scenario_dir / "valid.json").write_text(
        json.dumps(_valid_scenario()),
        encoding="utf-8",
    )
    (scenario_dir / "invalid.json").write_bytes(b"\xff\xfe")

    result = _run_tool(
        "--scenario-dir",
        str(scenario_dir),
        "--output-dir",
        str(output_dir),
        "--seed",
        "42",
    )

    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    index = json.loads((output_dir / "index.json").read_text(encoding="utf-8"))
    assert index["total"] == 2
    assert index["parse_failures"] == 1
    assert index["passed_runtime"] == 1
    assert sum(index["processing_outcomes"].values()) == 2


def test_cli_rejects_non_integer_seed_without_traceback(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "inputs"
    scenario_dir.mkdir()

    result = _run_tool("--scenario-dir", str(scenario_dir), "--seed", "not-an-int")

    assert result.returncode == 2
    assert "invalid int value" in result.stderr
    assert "Traceback" not in result.stderr


def test_missing_scenario_directory_is_a_fatal_setup_error(tmp_path: Path) -> None:
    result = _run_tool("--scenario-dir", str(tmp_path / "missing"))

    assert result.returncode == 1
    assert "Scenario directory not found" in result.stderr
    assert "Traceback" not in result.stderr
