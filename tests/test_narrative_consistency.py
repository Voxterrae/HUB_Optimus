from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "tools" / "check_narrative_consistency.py"
SEED_PATH = REPO_ROOT / "datasets" / "ai_risk_narratives" / "seed_claims.json"
TAXONOMY_PATH = REPO_ROOT / "datasets" / "ai_risk_narratives" / "taxonomy.json"


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _run_checker(input_path: Path, report_path: Path, summary_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    args = [
        sys.executable,
        str(CHECKER),
        "--input",
        str(input_path),
        "--taxonomy",
        str(TAXONOMY_PATH),
        "--report",
        str(report_path),
    ]
    if summary_path is not None:
        args.extend(["--summary-file", str(summary_path)])

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def _sample_record() -> dict[str, object]:
    records = _load_json(SEED_PATH)
    assert isinstance(records, list)
    record = deepcopy(records[0])
    assert isinstance(record, dict)
    return record


def test_current_dataset_has_no_consistency_errors(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    summary_path = tmp_path / "summary.md"

    proc = _run_checker(SEED_PATH, report_path, summary_path)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = _load_json(report_path)
    assert report["summary"]["errors"] == 0
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "## Narrative Consistency" in summary_text


def test_invalid_promotion_emits_warning(tmp_path: Path) -> None:
    record = _sample_record()
    record["claim_id"] = "NR-101"
    record["source_type"] = "unknown"
    record["verification_status"] = "verified"
    record["evidence_tier"] = "unknown"

    input_path = tmp_path / "dataset.json"
    report_path = tmp_path / "report.json"
    _write_json(input_path, [record])

    proc = _run_checker(input_path, report_path)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = _load_json(report_path)
    assert report["summary"]["warnings"] >= 1
    assert any(issue["type"] == "invalid_promotion" for issue in report["issues"])


def test_source_evidence_mismatch_emits_warning(tmp_path: Path) -> None:
    record = _sample_record()
    record["claim_id"] = "NR-102"
    record["source_type"] = "primary"
    record["evidence_tier"] = "unknown"
    record["verification_status"] = "mixed"

    input_path = tmp_path / "dataset.json"
    report_path = tmp_path / "report.json"
    _write_json(input_path, [record])

    proc = _run_checker(input_path, report_path)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = _load_json(report_path)
    assert any(issue["type"] == "source_evidence_mismatch" for issue in report["issues"])


def test_missing_required_field_emits_error(tmp_path: Path) -> None:
    record = _sample_record()
    record["claim_id"] = "NR-103"
    record.pop("source_shown", None)

    input_path = tmp_path / "dataset.json"
    report_path = tmp_path / "report.json"
    _write_json(input_path, [record])

    proc = _run_checker(input_path, report_path)

    assert proc.returncode == 1, proc.stdout + proc.stderr
    report = _load_json(report_path)
    assert report["summary"]["errors"] >= 1
    assert any(issue["type"] == "missing_required_field" for issue in report["issues"])


def test_duplicate_claim_text_emits_info(tmp_path: Path) -> None:
    first = _sample_record()
    second = deepcopy(first)
    first["claim_id"] = "NR-104"
    second["claim_id"] = "NR-105"

    input_path = tmp_path / "dataset.json"
    report_path = tmp_path / "report.json"
    _write_json(input_path, [first, second])

    proc = _run_checker(input_path, report_path)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = _load_json(report_path)
    assert report["summary"]["info"] >= 1
    assert any(issue["type"] == "duplicate_claim_text" for issue in report["issues"])
