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


def test_cli_output_file_writes_contractual_json_and_keeps_stdout_empty(tmp_path):
    output_path = tmp_path / "outputs" / "analysis_result.json"

    result = run_cli(
        "analyze",
        "examples/semantic_engine/case_minimal.json",
        "--output",
        str(output_path),
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["case_id"] == "case-minimal-001"
    assert payload["status"] == "draft"
    assert payload["claims"] == []
    assert output_path.read_text(encoding="utf-8").endswith("\n")


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


def test_cli_analyze_preserves_structured_claims_and_evidence():
    result = run_cli("analyze", "examples/semantic_engine/case_with_claims.json")

    assert result.returncode == 0
    assert result.stderr == ""

    payload = json.loads(result.stdout)
    assert payload["case_id"] == "case-claims-001"
    assert payload["status"] == "draft"
    assert payload["operational_signal"] == "triage"

    assert payload["claims"] == [
        {
            "claim_id": "claim-001",
            "text": "A submitted case reports unresolved status visibility in a public-facing process.",
            "source_ref": "operator-submission",
            "claim_type": "operational-friction",
            "requires_evidence": True,
            "status": "pending",
            "metadata": {
                "priority": "review",
            },
        }
    ]

    assert payload["evidence"] == [
        {
            "evidence_id": "evidence-001",
            "text": "The submitted timeline says the expected window was exceeded and communication channels did not resolve the case.",
            "source_ref": "operator-submission",
            "source_type": "statement",
            "supports_claim_ids": ["claim-001"],
            "contradicts_claim_ids": [],
            "limitations": [
                "User-submitted account; administrative records still need verification.",
            ],
            "metadata": {},
        }
    ]

    assert payload["inferences"] == [
        "Further verification is required before treating the claim as established."
    ]
    assert payload["uncertainties"] == [
        "The cause of the delay is not established from the submitted case alone."
    ]
    assert payload["narrative_amplification"] == [
        "Avoid generalizing from one submitted case to a full institution."
    ]
    assert payload["metadata"] == {
        "intake_channel": "operator-console-demo",
    }
