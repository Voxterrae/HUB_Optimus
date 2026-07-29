from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "datasets" / "ai_risk_narratives"
BENCHMARK_RUNNER = REPO_ROOT / "benchmarks" / "run_narrative_benchmarks.py"
REPORT_RENDERER = REPO_ROOT / "tools" / "render_narrative_report.py"
SEED_PATH = DATASET_DIR / "seed_claims.json"
CLAIM_SCHEMA_PATH = DATASET_DIR / "claim_record.schema.json"
REPORT_SCHEMA_PATH = DATASET_DIR / "narrative_report.schema.json"
DATASET_README_PATH = DATASET_DIR / "README.md"
NARRATIVE_INPUTS_DIR = REPO_ROOT / "benchmarks" / "narrative" / "inputs"
NARRATIVE_EXPECTED_DIR = REPO_ROOT / "benchmarks" / "narrative" / "expected"
CLAIM_REQUIRED_FIELDS = (
    "claim_id",
    "claim_text",
    "source_shown",
    "source_type",
    "approx_date",
    "risk_domain",
    "verification_status",
    "evidence_tier",
    "jurisdiction",
    "notes",
)


EXPECTED_CLOSED_VOCABULARIES = {
    "risk_domain": [
        "privacy",
        "biometrics",
        "surveillance",
        "browser_security",
        "copyright",
        "defense",
        "labor",
        "environment",
        "hardware",
        "local_vs_cloud",
    ],
    "verification_status": [
        "verified",
        "mixed",
        "misleading",
        "unsupported",
    ],
    "evidence_tier": [
        "primary",
        "official_secondary",
        "reputable_press",
        "advocacy",
        "unknown",
    ],
}


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def _iter_json_lists(payload: object) -> list[list[object]]:
    lists: list[list[object]] = []
    if isinstance(payload, list):
        lists.append(payload)
        for item in payload:
            lists.extend(_iter_json_lists(item))
    elif isinstance(payload, dict):
        for value in payload.values():
            lists.extend(_iter_json_lists(value))
    return lists


def test_claim_schema_is_the_only_stored_closed_taxonomy() -> None:
    schema = _load_json(CLAIM_SCHEMA_PATH)

    assert isinstance(schema, dict)
    assert not (DATASET_DIR / "taxonomy.json").exists()

    for name, expected_values in EXPECTED_CLOSED_VOCABULARIES.items():
        assert schema["$defs"][name]["enum"] == expected_values
        assert schema["properties"][name] == {"$ref": f"#/$defs/{name}"}

        occurrences = [
            path
            for path in DATASET_DIR.glob("*.json")
            for values in _iter_json_lists(_load_json(path))
            if values == expected_values
        ]
        assert occurrences == [CLAIM_SCHEMA_PATH]


def test_seed_claims_validate_against_schema() -> None:
    schema = _load_json(CLAIM_SCHEMA_PATH)
    records = _load_json(SEED_PATH)
    validator = jsonschema.Draft202012Validator(schema)

    assert isinstance(records, list)
    assert len(records) == 16
    for record in records:
        errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
        assert errors == [], [error.message for error in errors]


def test_claim_schema_explicitly_rejects_invalid_risk_domain() -> None:
    schema = _load_json(CLAIM_SCHEMA_PATH)
    records = _load_json(SEED_PATH)
    assert isinstance(records, list)
    record = deepcopy(records[0])
    record["risk_domain"] = "free_text_domain"

    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(record))

    assert any(
        error.validator == "enum" and list(error.path) == ["risk_domain"]
        for error in errors
    )


@pytest.mark.parametrize("required_field", CLAIM_REQUIRED_FIELDS)
def test_claim_schema_explicitly_rejects_each_missing_required_field(
    required_field: str,
) -> None:
    schema = _load_json(CLAIM_SCHEMA_PATH)
    records = _load_json(SEED_PATH)
    assert isinstance(records, list)
    record = deepcopy(records[0])
    record.pop(required_field)

    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(record))

    assert any(
        error.validator == "required" and required_field in error.message
        for error in errors
    )


def test_seed_corpus_is_literal_provisional_and_row_reviewable() -> None:
    records = _load_json(SEED_PATH)
    readme = DATASET_README_PATH.read_text(encoding="utf-8")

    assert isinstance(records, list)
    assert [record["claim_id"] for record in records] == [
        f"NR-{index:03d}" for index in range(1, 17)
    ]
    assert all(record["claim_text"].strip() for record in records)
    assert all(record["source_shown"].strip() for record in records)
    assert all(record["notes"].strip() for record in records)
    assert "screenshot text as dirty input" in readme
    assert "literal transcription set" in readme
    assert "seed remains provisional" in readme


def test_seed_claims_cover_all_verification_statuses() -> None:
    records = _load_json(SEED_PATH)
    statuses = {record["verification_status"] for record in records}
    assert statuses == {"verified", "mixed", "misleading", "unsupported"}


def test_narrative_benchmark_inputs_validate_against_report_schema() -> None:
    schema = _load_json(REPORT_SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema)

    input_files = sorted(NARRATIVE_INPUTS_DIR.glob("*.json"))
    assert input_files
    for input_file in input_files:
        payload = _load_json(input_file)
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
        assert errors == [], [error.message for error in errors]


def test_renderer_emits_required_sections(tmp_path: Path) -> None:
    output_path = tmp_path / "report.md"
    sample_input = NARRATIVE_INPUTS_DIR / "chrome_gemini_bug.json"

    proc = _run(str(REPORT_RENDERER), str(sample_input), "--output", str(output_path))

    assert proc.returncode == 0, proc.stderr
    text = output_path.read_text(encoding="utf-8")
    assert "## Claim" in text
    assert "## Evidence" in text
    assert "## Inference" in text
    assert "## Mitigation" in text


@pytest.mark.parametrize("missing_section", ("evidence", "mitigation"))
def test_renderer_rejects_missing_evidence_or_mitigation(
    tmp_path: Path,
    missing_section: str,
) -> None:
    sample_input = NARRATIVE_INPUTS_DIR / "chrome_gemini_bug.json"
    payload = _load_json(sample_input)
    assert isinstance(payload, dict)
    payload.pop(missing_section)
    invalid_input = tmp_path / f"missing-{missing_section}.json"
    invalid_input.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "report.md"

    proc = _run(str(REPORT_RENDERER), str(invalid_input), "--output", str(output_path))

    assert proc.returncode == 1
    assert "[narrative-report:error]" in proc.stderr
    assert f"'{missing_section}' is a required property" in proc.stderr
    assert not output_path.exists()


def test_narrative_benchmarks_cover_required_handling_styles() -> None:
    input_files = sorted(NARRATIVE_INPUTS_DIR.glob("*.json"))
    assert len(input_files) == 5

    required_cases = {
        "nigeria_tracking_verified": (
            "verified",
            "supports the narrow announcement claim",
        ),
        "dod_contract_red_lines": ("mixed", "This is a mixed defense claim"),
        "perplexity_italy_copyright": (
            "unsupported",
            "Treat this as unsupported",
        ),
    }
    assert {status for status, _ in required_cases.values()} == {
        "verified",
        "mixed",
        "unsupported",
    }

    for case_name, (_, marker) in required_cases.items():
        payload = _load_json(NARRATIVE_INPUTS_DIR / f"{case_name}.json")
        assert isinstance(payload, dict)
        assert marker in payload["inference"]
        expected = (
            NARRATIVE_EXPECTED_DIR / f"{case_name}.md"
        ).read_text(encoding="utf-8")
        assert marker in expected


def test_narrative_benchmarks_pass() -> None:
    first = _run(str(BENCHMARK_RUNNER))
    second = _run(str(BENCHMARK_RUNNER))

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert second.stdout == first.stdout
