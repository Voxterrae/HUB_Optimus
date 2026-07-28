import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from semantic_engine.cli.__main__ import build_draft_result
from semantic_engine.contracts.case_input import (
    CaseInputValidationError,
    load_case_input_schema,
    validate_case_input,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = ROOT / "examples" / "semantic_engine" / "case_with_claims.json"


def example_case():
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def run_cli(path: Path):
    return subprocess.run(
        [sys.executable, "-m", "semantic_engine.cli", "analyze", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def assert_json_subset(expected, actual):
    if isinstance(expected, dict):
        assert isinstance(actual, dict)
        for key, value in expected.items():
            assert key in actual
            assert_json_subset(value, actual[key])
        return
    if isinstance(expected, list):
        assert isinstance(actual, list)
        assert len(actual) == len(expected)
        for expected_item, actual_item in zip(expected, actual):
            assert_json_subset(expected_item, actual_item)
        return
    assert actual == expected


def test_case_input_schema_is_versioned_and_accepts_repository_examples():
    schema = load_case_input_schema()

    assert schema["$id"].endswith("/case-input-v1.schema.json")
    validate_case_input(example_case())
    validate_case_input(
        json.loads(
            (
                ROOT / "examples" / "semantic_engine" / "case_minimal.json"
            ).read_text(encoding="utf-8")
        )
    )


@pytest.mark.parametrize(
    ("mutate", "expected_path"),
    [
        (
            lambda payload: payload.__setitem__("operational_singal", "triage"),
            "$.operational_singal",
        ),
        (
            lambda payload: payload["claims"][0].__setitem__(
                "unexpected_truth_score",
                0.99,
            ),
            "$.claims[0].unexpected_truth_score",
        ),
        (
            lambda payload: payload.__setitem__("decision_trace", []),
            "$.decision_trace",
        ),
    ],
)
def test_unknown_and_output_only_fields_are_rejected_at_exact_path(
    mutate,
    expected_path,
):
    payload = example_case()
    mutate(payload)

    with pytest.raises(
        CaseInputValidationError,
        match=rf"^{re.escape(expected_path)}:",
    ):
        validate_case_input(payload)


@pytest.mark.parametrize(
    ("collection", "id_field", "expected_path"),
    [
        ("claims", "claim_id", "$.claims[1].claim_id"),
        ("evidence", "evidence_id", "$.evidence[1].evidence_id"),
    ],
)
def test_duplicate_record_ids_are_rejected_at_second_record(
    collection,
    id_field,
    expected_path,
):
    payload = example_case()
    payload[collection].append(copy.deepcopy(payload[collection][0]))

    with pytest.raises(
        CaseInputValidationError,
        match=rf"^{re.escape(expected_path)}: duplicate",
    ):
        validate_case_input(payload)


@pytest.mark.parametrize(
    ("field_name", "expected_path"),
    [
        ("supports_claim_ids", "$.evidence[0].supports_claim_ids[1]"),
        ("contradicts_claim_ids", "$.evidence[0].contradicts_claim_ids[0]"),
    ],
)
def test_dangling_evidence_references_are_rejected_at_exact_path(
    field_name,
    expected_path,
):
    payload = example_case()
    payload["evidence"][0].setdefault(field_name, []).append("missing-claim")

    with pytest.raises(
        CaseInputValidationError,
        match=rf"^{re.escape(expected_path)}: unknown",
    ):
        validate_case_input(payload)


def test_accepted_fields_and_open_metadata_round_trip_without_loss():
    payload = example_case()
    payload["status"] = "draft"
    payload["metadata"]["extension"] = {"reviewers": ["human"], "score": None}
    payload["metadata"]["decision_trace"] = [{"claim": "opaque only"}]
    payload["claims"][0]["metadata"]["custom_flag"] = True
    payload["evidence"][0]["metadata"] = {"source_snapshot": {"retained": True}}

    result = build_draft_result(payload).to_dict()

    assert_json_subset(payload, result)
    assert result["decision_trace"] == []
    assert result["audit_log"] == []


def test_cli_reports_controlled_json_path_without_traceback(tmp_path):
    payload = example_case()
    payload["claims"][0]["claim_id"] = "claim-duplicate"
    duplicate = copy.deepcopy(payload["claims"][0])
    payload["claims"].append(duplicate)
    case_path = tmp_path / "invalid-case.json"
    case_path.write_text(json.dumps(payload), encoding="utf-8")

    result = run_cli(case_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert (
        "semantic_engine.cli: error: $.claims[1].claim_id: duplicate claim_id"
        in result.stderr
    )
    assert "Traceback" not in result.stderr


def test_operator_and_api_handoff_reach_the_same_cli_contract():
    operator = (ROOT / "site" / "operator" / "index.html").read_text(
        encoding="utf-8"
    )
    api = (ROOT / "ops" / "ec2" / "hub-api.sh").read_text(encoding="utf-8")
    core = (ROOT / "ops" / "ec2" / "hub-core.sh").read_text(encoding="utf-8")

    assert "http://127.0.0.1:8080/analyze" in operator
    assert '"/opt/hub-optimus/shared/bin/hub-core"' in api
    assert '"analyze"' in api
    assert "python -m semantic_engine.cli analyze" in core
