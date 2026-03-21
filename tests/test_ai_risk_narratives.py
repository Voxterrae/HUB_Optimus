from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "datasets" / "ai_risk_narratives"
BENCHMARK_RUNNER = REPO_ROOT / "benchmarks" / "run_narrative_benchmarks.py"
REPORT_RENDERER = REPO_ROOT / "tools" / "render_narrative_report.py"
SEED_PATH = DATASET_DIR / "seed_claims.json"
CLAIM_SCHEMA_PATH = DATASET_DIR / "claim_record.schema.json"
REPORT_SCHEMA_PATH = DATASET_DIR / "narrative_report.schema.json"
TAXONOMY_PATH = DATASET_DIR / "taxonomy.json"
NARRATIVE_INPUTS_DIR = REPO_ROOT / "benchmarks" / "narrative" / "inputs"


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


def test_taxonomy_and_claim_schema_are_aligned() -> None:
    taxonomy = _load_json(TAXONOMY_PATH)
    schema = _load_json(CLAIM_SCHEMA_PATH)

    assert isinstance(taxonomy, dict)
    assert isinstance(schema, dict)
    assert taxonomy["risk_domains"] == schema["properties"]["risk_domain"]["enum"]
    assert taxonomy["verification_statuses"] == schema["properties"]["verification_status"]["enum"]
    assert taxonomy["evidence_tiers"] == schema["properties"]["evidence_tier"]["enum"]


def test_seed_claims_validate_against_schema() -> None:
    schema = _load_json(CLAIM_SCHEMA_PATH)
    records = _load_json(SEED_PATH)
    validator = jsonschema.Draft202012Validator(schema)

    assert isinstance(records, list)
    assert 15 <= len(records) <= 20
    for record in records:
        errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
        assert errors == [], [error.message for error in errors]


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


def test_narrative_benchmarks_pass() -> None:
    proc = _run(str(BENCHMARK_RUNNER))
    assert proc.returncode == 0, proc.stdout + proc.stderr
