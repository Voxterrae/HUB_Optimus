"""
Scenario telemetry collector for HUB_Optimus.

Runs every scenario in a target directory through the simulator, captures
structured telemetry per execution, and writes:

  scenarios/telemetry.json   — array of per-scenario records
  scenarios/index.json       — aggregate statistics

Each telemetry record captures:
  scenario_id, family, actors, max_rounds, result_status,
  rounds_used, convergence_round, schema_valid, runtime_error

Usage:
  python tools/scenario_telemetry.py                          # default dirs
  python tools/scenario_telemetry.py --scenario-dir DIR       # custom input
  python tools/scenario_telemetry.py --seed 99                # different seed
"""

from __future__ import annotations

import argparse
import json
import subprocess
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "run_scenario.py"
SCHEMA_PATH = REPO_ROOT / "scenario.schema.json"
DEFAULT_SCENARIO_DIR = REPO_ROOT / "scenarios" / "generated"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "scenarios"
SEED = "42"
PROCESSING_OUTCOMES = (
    "agreement",
    "no_agreement",
    "parse_error",
    "schema_error",
    "runtime_error",
)
PARTIAL_ERROR_OUTCOMES = {"parse_error", "schema_error", "runtime_error"}


# ── Telemetry collection ───────────────────────────────────


def _infer_family(path: Path) -> str:
    """Infer the scenario family from its parent directory or filename."""
    # If organized in family subdirectories, use the parent dir name
    parent = path.parent.name
    if parent != "generated":
        return parent
    # Fall back to filename prefix (e.g. info_asymmetry_001 → info_asymmetry)
    parts = path.stem.rsplit("_", 1)
    return parts[0] if len(parts) == 2 and parts[1].isdigit() else path.stem


def _infer_mutation_axis(path: Path) -> str | None:
    """Return the mutation axis if the scenario is a mutation, else None."""
    if "mutations" in path.parts:
        return path.parent.name
    return None


def _validate_schema(payload: Any) -> bool:
    """Check if the scenario payload passes schema validation."""
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return not list(validator.iter_errors(payload))


def collect_one(scenario_path: Path, seed: int) -> dict[str, Any]:
    """Run one scenario and return a telemetry record."""
    scenario_id = scenario_path.stem
    family = _infer_family(scenario_path)

    record: dict[str, Any] = {
        "scenario_id": scenario_id,
        "family": family,
        "mutation_axis": _infer_mutation_axis(scenario_path),
        "seed": seed,
        "actors": 0,
        "max_rounds": 0,
        "result_status": "error",
        "rounds_used": 0,
        "convergence_round": None,
        "schema_valid": False,
        "runtime_error": False,
        "processing_outcome": "parse_error",
        "error_code": None,
    }

    # Load and validate schema
    try:
        payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        record["error_code"] = "invalid_utf8"
        return record
    except json.JSONDecodeError:
        record["error_code"] = "invalid_json"
        return record
    except OSError:
        record["error_code"] = "read_error"
        return record

    if not isinstance(payload, dict):
        record["error_code"] = "json_root_not_object"
        return record

    record["schema_valid"] = _validate_schema(payload)
    if not record["schema_valid"]:
        record["processing_outcome"] = "schema_error"
        record["error_code"] = "schema_invalid"
        return record

    record["actors"] = len(payload["roles"])
    record["max_rounds"] = payload["max_rounds"]

    # Run through the simulator
    record["processing_outcome"] = "runtime_error"
    record["runtime_error"] = True
    actual = scenario_path.with_suffix(".telemetry_tmp.json")
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [
                sys.executable, str(RUNNER),
                str(scenario_path),
                "--output", str(actual),
                "--seed", str(seed),
            ],
            cwd=REPO_ROOT,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env=env, check=False,
        )

        if proc.returncode != 0:
            record["error_code"] = "runner_exit"
            return record

        result = json.loads(actual.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            record["error_code"] = "runner_output_not_object"
            return record

        result_status = result.get("status")
        rounds_used = result.get("rounds")
        if result_status not in {"success", "failure"}:
            record["error_code"] = "runner_status_invalid"
            return record
        if not isinstance(rounds_used, int) or isinstance(rounds_used, bool) or rounds_used < 0:
            record["error_code"] = "runner_rounds_invalid"
            return record

        record["runtime_error"] = False
        record["result_status"] = result_status
        record["rounds_used"] = rounds_used
        record["processing_outcome"] = (
            "agreement" if result_status == "success" else "no_agreement"
        )
        record["error_code"] = None

        if result_status == "success":
            record["convergence_round"] = rounds_used
    except UnicodeDecodeError:
        record["error_code"] = "runner_output_invalid_utf8"
    except json.JSONDecodeError:
        record["error_code"] = "runner_output_invalid_json"
    except OSError:
        record["error_code"] = "runner_output_error"
    finally:
        try:
            actual.unlink(missing_ok=True)
        except OSError:
            pass

    return record


def collect_all(scenario_dir: Path, seed: int) -> list[dict[str, Any]]:
    """Collect telemetry for all scenarios in a directory (recursive)."""
    skip = {"telemetry.json", "index.json"}
    scenarios = sorted(
        p for p in scenario_dir.rglob("*.json")
        if p.name not in skip and ".telemetry_tmp" not in p.name
    )
    records: list[dict[str, Any]] = []

    for path in scenarios:
        record = collect_one(path, seed)
        status_icon = {
            "agreement": "\u2705",
            "no_agreement": "\u274c",
            "parse_error": "\U0001f6a8",
            "schema_error": "\U0001f6a8",
            "runtime_error": "\U0001f6a8",
        }[record["processing_outcome"]]
        print(f"  {status_icon}  {record['scenario_id']}  "
              f"[{record['family']}] "
              f"outcome={record['processing_outcome']} "
              f"rounds={record['rounds_used']}/{record['max_rounds']}")
        records.append(record)

    return records


# ── Index generation ────────────────────────────────────────


def build_index(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build aggregate statistics from telemetry records."""
    total = len(records)
    outcome_counts = {
        outcome: sum(1 for record in records if record["processing_outcome"] == outcome)
        for outcome in PROCESSING_OUTCOMES
    }
    agreements = outcome_counts["agreement"]
    no_agreements = outcome_counts["no_agreement"]
    passed = agreements + no_agreements
    parse_failures = outcome_counts["parse_error"]
    schema_invalid = outcome_counts["schema_error"]
    runtime_failures = outcome_counts["runtime_error"]

    convergence_rounds = [
        r["convergence_round"]
        for r in records
        if r["processing_outcome"] == "agreement"
        and r["convergence_round"] is not None
    ]
    avg_convergence = (
        round(sum(convergence_rounds) / len(convergence_rounds), 2)
        if convergence_rounds else None
    )

    # Per-family breakdown
    families: dict[str, dict[str, Any]] = {}
    for r in records:
        fam = r["family"]
        if fam not in families:
            families[fam] = {"total": 0, "agreements": 0, "failures": 0, "errors": 0}
        families[fam]["total"] += 1
        if r["processing_outcome"] == "agreement":
            families[fam]["agreements"] += 1
        elif r["processing_outcome"] == "no_agreement":
            families[fam]["failures"] += 1
        if r["processing_outcome"] in PARTIAL_ERROR_OUTCOMES:
            families[fam]["errors"] += 1

    return {
        "total": total,
        "passed_runtime": passed,
        "parse_failures": parse_failures,
        "schema_invalid": schema_invalid,
        "runtime_failures": runtime_failures,
        "agreements": agreements,
        "no_agreements": no_agreements,
        "avg_convergence_round": avg_convergence,
        "processing_outcomes": outcome_counts,
        "by_family": families,
    }


# ── Output ──────────────────────────────────────────────────


def write_telemetry(records: list[dict[str, Any]], output_dir: Path) -> Path:
    """Write per-scenario telemetry to output_dir/telemetry.json."""
    path = output_dir / "telemetry.json"
    path.write_text(
        json.dumps(records, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def write_index(index: dict[str, Any], output_dir: Path) -> Path:
    """Write aggregate index to output_dir/index.json."""
    path = output_dir / "index.json"
    path.write_text(
        json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def print_summary(index: dict[str, Any]) -> None:
    """Print a human-readable summary to stdout."""
    print(f"\n{'=' * 50}")
    print("  Scenario Telemetry Summary")
    print(f"{'=' * 50}")
    print(f"  Total scenarios:       {index['total']}")
    print(f"  Passed runtime:        {index['passed_runtime']}")
    print(f"  Parse failures:        {index['parse_failures']}")
    print(f"  Schema invalid:        {index['schema_invalid']}")
    print(f"  Runtime failures:      {index['runtime_failures']}")
    print(f"  Agreements reached:    {index['agreements']}")
    print(f"  No agreement:          {index['no_agreements']}")
    if index["avg_convergence_round"] is not None:
        print(f"  Avg convergence round: {index['avg_convergence_round']}")
    print()
    print("  By family:")
    for fam, stats in sorted(index["by_family"].items()):
        agree_rate = (
            f"{stats['agreements']}/{stats['total']}"
            if stats["total"] > 0 else "-"
        )
        print(f"    {fam}: {stats['total']} scenarios, "
              f"{agree_rate} agreements, "
              f"{stats['errors']} errors")
    print(f"{'=' * 50}")


# ── CLI ─────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect execution telemetry for generated scenarios."
    )
    parser.add_argument(
        "--scenario-dir", type=str, default=None,
        help=f"Directory with scenario JSON files (default: {DEFAULT_SCENARIO_DIR}).",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help=f"Where to write telemetry.json and index.json (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--seed", type=int, default=int(SEED),
        help=f"Seed for reproducible runs (default: {SEED}).",
    )
    args = parser.parse_args()

    scenario_dir = Path(args.scenario_dir) if args.scenario_dir else DEFAULT_SCENARIO_DIR
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR

    if not scenario_dir.is_dir():
        print(f"Scenario directory not found: {scenario_dir}", file=sys.stderr)
        print("Run the generator first:\n"
              "  python tools/scenario_generator/generate_scenarios.py",
              file=sys.stderr)
        return 1

    print(f"Collecting telemetry from {scenario_dir} ...\n")
    try:
        records = collect_all(scenario_dir, args.seed)
    except OSError as exc:
        print(f"Unable to scan scenario directory: {exc}", file=sys.stderr)
        return 1

    if not records:
        print("No scenarios found.", file=sys.stderr)
        return 1

    index = build_index(records)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        tel_path = write_telemetry(records, output_dir)
        idx_path = write_index(index, output_dir)
    except OSError as exc:
        print(f"Unable to write telemetry output: {exc}", file=sys.stderr)
        return 1

    print_summary(index)
    print(f"\n  telemetry → {tel_path}")
    print(f"  index     → {idx_path}")
    return 2 if any(index["processing_outcomes"][name] for name in PARTIAL_ERROR_OUTCOMES) else 0


if __name__ == "__main__":
    raise SystemExit(main())
