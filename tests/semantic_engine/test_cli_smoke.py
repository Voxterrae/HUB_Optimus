import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "semantic_engine.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_analyze_happy_path_outputs_contractual_json():
    result = run_cli("analyze", "examples/semantic_engine/case_minimal.json")

    assert result.returncode == 0
    assert result.stderr == ""

    payload = json.loads(result.stdout)
    assert payload["case_id"] == "case-minimal-001"
    assert payload["core_version_ref"] == "main"
    assert payload["input_summary"] == "Minimal CLI smoke case for Semantic Engine contracts."
    assert payload["claims"] == []
    assert payload["evidence"] == []
    assert payload["inferences"] == []
    assert payload["uncertainties"] == []
    assert payload["narrative_amplification"] == []
    assert payload["operational_signal"] == "none"
    assert payload["status"] == "draft"
    assert payload["decision_trace"] == []
    assert payload["audit_log"] == []


def test_cli_missing_file_fails_cleanly():
    result = run_cli("analyze", "examples/semantic_engine/does_not_exist.json")

    assert result.returncode == 1
    assert result.stdout == ""
    assert "semantic_engine.cli: error: input file not found" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_invalid_json_fails_cleanly(tmp_path):
    case_path = tmp_path / "invalid.json"
    case_path.write_text("{not json", encoding="utf-8")

    result = run_cli("analyze", str(case_path))

    assert result.returncode == 1
    assert result.stdout == ""
    assert "semantic_engine.cli: error: invalid JSON" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_missing_required_field_fails_cleanly(tmp_path):
    case_path = tmp_path / "missing.json"
    write_json(
        case_path,
        {
            "case_id": "case-missing-001",
            "core_version_ref": "main",
        },
    )

    result = run_cli("analyze", str(case_path))

    assert result.returncode == 1
    assert result.stdout == ""
    assert "semantic_engine.cli: error: missing required string field: input_summary" in result.stderr
    assert "Traceback" not in result.stderr
