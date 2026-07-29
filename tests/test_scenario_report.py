"""Tests for the human-readable scenario telemetry report."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = REPO_ROOT / "tools" / "scenario_report.py"


def _load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("scenario_report", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _record(
    family: str,
    outcome: str,
    convergence_round: int | None = None,
    **overrides: object,
) -> dict[str, object]:
    if outcome == "agreement":
        rounds_used = (
            convergence_round
            if isinstance(convergence_round, int)
            and not isinstance(convergence_round, bool)
            else 1
        )
        max_rounds = max(convergence_round or 0, 1)
        result_status = "success"
        schema_valid = True
        runtime_error = False
        error_code = None
    elif outcome == "no_agreement":
        rounds_used = 3
        max_rounds = 3
        result_status = "failure"
        schema_valid = True
        runtime_error = False
        error_code = None
    else:
        rounds_used = 0
        max_rounds = 0
        result_status = "error"
        schema_valid = False
        runtime_error = outcome == "runtime_error"
        error_code = f"fixture_{outcome}"
    record = {
        "family": family,
        "processing_outcome": outcome,
        "convergence_round": convergence_round,
        "result_status": result_status,
        "rounds_used": rounds_used,
        "max_rounds": max_rounds,
        "schema_valid": schema_valid,
        "runtime_error": runtime_error,
        "error_code": error_code,
    }
    record.update(overrides)
    return record


def _write_telemetry(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(records, ensure_ascii=False),
        encoding="utf-8",
    )


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


def test_plain_text_aggregates_current_outcomes_by_family(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.json"
    _write_telemetry(
        telemetry,
        [
            _record("resource_scarcity", "agreement", 1),
            _record("resource_scarcity", "agreement", 3),
            _record("resource_scarcity", "no_agreement"),
            _record("resource_scarcity", "schema_error"),
            _record("info_asymmetry", "agreement", 2),
        ],
    )

    result = _run_tool(str(telemetry))

    assert result.returncode == 0
    assert result.stderr == ""
    assert (
        "info_asymmetry     1          1          100%                     "
        "2                        0         0"
        in result.stdout
    )
    assert (
        "resource_scarcity  4          3          66.67%                   "
        "2                        1         1"
        in result.stdout
    )


def test_markdown_produces_valid_table_and_escapes_family(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.json"
    _write_telemetry(
        telemetry,
        [_record("family|variant", "agreement", 2)],
    )

    result = _run_tool(str(telemetry), "--markdown")

    assert result.returncode == 0
    assert result.stdout == (
        "| Family | Scenarios | Completed | Agreement % (completed) | "
        "Avg Rounds (agreements) | Failures | Errors |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| family\\|variant | 1 | 1 | 100% | 2 | 0 | 0 |\n"
    )


def test_output_flag_writes_report_instead_of_stdout(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.json"
    output = tmp_path / "report.md"
    _write_telemetry(telemetry, [_record("fixture", "no_agreement")])

    result = _run_tool(
        str(telemetry),
        "--markdown",
        "--output",
        str(output),
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert "| fixture | 1 | 1 | 0% | - | 1 | 0 |\n" in output.read_text(
        encoding="utf-8"
    )


def test_output_cannot_replace_telemetry_through_same_path_or_hardlink(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    _write_telemetry(telemetry, [_record("fixture", "agreement", 2)])
    original = telemetry.read_bytes()

    same_path = _run_tool(str(telemetry), "--output", str(telemetry))

    assert same_path.returncode == 1
    assert "output file must not replace the telemetry input" in same_path.stderr
    assert telemetry.read_bytes() == original

    hardlink = tmp_path / "report.txt"
    hardlink.hardlink_to(telemetry)
    linked = _run_tool(str(telemetry), "--output", str(hardlink))

    assert linked.returncode == 1
    assert "output file must not replace the telemetry input" in linked.stderr
    assert telemetry.read_bytes() == original


def test_atomic_output_does_not_follow_target_swapped_after_validation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    report = _load_tool()
    telemetry = tmp_path / "telemetry.json"
    output = tmp_path / "report.txt"
    _write_telemetry(telemetry, [_record("fixture", "agreement", 2)])
    original = telemetry.read_bytes()
    original_validation = report._validate_output_target

    def validate_then_swap(source: Path, destination: Path):
        target = original_validation(source, destination)
        destination.hardlink_to(source)
        return target

    monkeypatch.setattr(report, "_validate_output_target", validate_then_swap)

    assert report.main([str(telemetry), "--output", str(output)]) == 0
    assert telemetry.read_bytes() == original
    assert not telemetry.samefile(output)
    assert "fixture" in output.read_text(encoding="utf-8")


def test_atomic_output_rejects_parent_directory_swap(
    tmp_path: Path,
) -> None:
    report = _load_tool()
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    moved_output_dir = tmp_path / "moved-output"
    source_dir.mkdir()
    output_dir.mkdir()
    telemetry = source_dir / "telemetry.json"
    output = output_dir / "telemetry.json"
    _write_telemetry(telemetry, [_record("fixture", "agreement", 2)])
    original = telemetry.read_bytes()
    target = report._validate_output_target(telemetry, output)

    output_dir.rename(moved_output_dir)
    output_dir.symlink_to(source_dir, target_is_directory=True)

    try:
        report._write_report_atomically(target, "unsafe replacement\n")
    except report.ReportInputError as exc:
        assert "output parent changed" in str(exc) or "cannot write report" in str(exc)
    else:
        raise AssertionError("parent swap must fail closed")
    assert telemetry.read_bytes() == original
    assert not (moved_output_dir / "telemetry.json").exists()


def test_missing_telemetry_is_controlled_exit_one(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"

    result = _run_tool(str(missing))

    assert result.returncode == 1
    assert "telemetry file not found" in result.stderr
    assert "Traceback" not in result.stderr


def test_invalid_root_is_controlled_exit_one(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.json"
    telemetry.write_text("{}\n", encoding="utf-8")

    result = _run_tool(str(telemetry))

    assert result.returncode == 1
    assert "telemetry root must be a JSON array" in result.stderr
    assert "Traceback" not in result.stderr


def test_family_cannot_inject_rows_or_ambiguous_whitespace(
    tmp_path: Path,
) -> None:
    for family in ("family\n| injected | row |", " family", "family\tvariant"):
        telemetry = tmp_path / "telemetry.json"
        _write_telemetry(telemetry, [_record(family, "agreement", 1)])

        result = _run_tool(str(telemetry), "--markdown")

        assert result.returncode == 1
        assert "family must be printable" in result.stderr
        assert "Traceback" not in result.stderr


def test_agreement_requires_a_positive_convergence_round(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.json"
    _write_telemetry(telemetry, [_record("fixture", "agreement")])

    result = _run_tool(str(telemetry))

    assert result.returncode == 1
    assert "convergence_round must be a positive integer" in result.stderr
    assert "Traceback" not in result.stderr


def test_unhashable_outcome_is_a_controlled_error(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.json"
    _write_telemetry(
        telemetry,
        [_record("fixture", "agreement", 1, processing_outcome=[])],
    )

    result = _run_tool(str(telemetry))

    assert result.returncode == 1
    assert "processing_outcome must be one of" in result.stderr
    assert "Traceback" not in result.stderr


def test_contradictory_telemetry_is_rejected_instead_of_reported(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    _write_telemetry(
        telemetry,
        [
            _record(
                "fixture",
                "agreement",
                999,
                result_status="failure",
                rounds_used=1,
                max_rounds=1,
                runtime_error=True,
                schema_valid=False,
            )
        ],
    )

    result = _run_tool(str(telemetry))

    assert result.returncode == 1
    assert "contradict" in result.stderr
    assert "100%" not in result.stdout
    assert "Traceback" not in result.stderr


def test_error_outcomes_match_shapes_emitted_by_collector(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.json"
    invalid_records = [
        _record("fixture", "parse_error", max_rounds=1),
        _record("fixture", "schema_error", max_rounds=1),
        _record(
            "fixture",
            "runtime_error",
            schema_valid=False,
            max_rounds=1,
        ),
    ]

    for record in invalid_records:
        _write_telemetry(telemetry, [record])
        result = _run_tool(str(telemetry))
        assert result.returncode == 1
        assert "contradict" in result.stderr
        assert "Traceback" not in result.stderr


def test_aggregation_keeps_processing_errors_out_of_behavior_rate() -> None:
    report = _load_tool()
    records = [
        _record("fixture", "agreement", 1),
        _record("fixture", "no_agreement"),
        _record("fixture", "runtime_error"),
    ]

    stats = report.aggregate_by_family(records)["fixture"]

    assert stats.scenarios == 3
    assert stats.agreements == 1
    assert stats.failures == 1
    assert stats.errors == 1
    assert stats.agreement_rate == 50
