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


def collect_one(scenario_path: Path, seed: str) -> dict[str, Any]:
    """Run one scenario and return a telemetry record."""
    scenario_id = scenario_path.stem
    family = _infer_family(scenario_path)

    record: dict[str, Any] = {
        "scenario_id": scenario_id,
        "family": family,
        "mutation_axis": _infer_mutation_axis(scenario_path),
        "seed": int(seed),
        "actors": 0,
        "max_rounds": 0,
        "result_status": "error",
        "rounds_used": 0,
        "convergence_round": None,
        "schema_valid": False,
        "runtime_error": True,
    }

    # Load and validate schema
    try:
        payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return record

    record["schema_valid"] = _validate_schema(payload)
    record["actors"] = len(payload.get("roles", []))
    record["max_rounds"] = payload.get("max_rounds", 0)

    if not record["schema_valid"]:
        return record

    # Run through the simulator
    actual = scenario_path.with_suffix(".telemetry_tmp.json")
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [
                sys.executable, str(RUNNER),
                str(scenario_path),
                "--output", str(actual),
                "--seed", seed,
            ],
            cwd=REPO_ROOT,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env=env, check=False,
        )

        if proc.returncode != 0:
            return record

        record["runtime_error"] = False
        result = json.loads(actual.read_text(encoding="utf-8"))
        record["result_status"] = result.get("status", "unknown")
        record["rounds_used"] = result.get("rounds", 0)

        if result.get("status") == "success":
            record["convergence_round"] = result.get("rounds")
    except (json.JSONDecodeError, OSError):
        pass
    finally:
        if actual.exists():
            actual.unlink()

    return record


def collect_all(scenario_dir: Path, seed: str) -> list[dict[str, Any]]:
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
            "success": "\u2705", "failure": "\u274c", "error": "\U0001f6a8",
        }.get(record["result_status"], "\u2753")
        print(f"  {status_icon}  {record['scenario_id']}  "
              f"[{record['family']}] "
              f"rounds={record['rounds_used']}/{record['max_rounds']}")
        records.append(record)

    return records


# ── Index generation ────────────────────────────────────────


def build_index(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build aggregate statistics from telemetry records."""
    total = len(records)
    schema_invalid = sum(1 for r in records if not r["schema_valid"])
    runtime_failures = sum(1 for r in records if r["runtime_error"])
    passed = total - schema_invalid - runtime_failures

    agreements = sum(1 for r in records if r["result_status"] == "success")
    no_agreements = sum(1 for r in records if r["result_status"] == "failure")

    convergence_rounds = [
        r["convergence_round"] for r in records if r["convergence_round"] is not None
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
        if r["result_status"] == "success":
            families[fam]["agreements"] += 1
        elif r["result_status"] == "failure":
            families[fam]["failures"] += 1
        if r["runtime_error"]:
            families[fam]["errors"] += 1

    return {
        "total": total,
        "passed_runtime": passed,
        "schema_invalid": schema_invalid,
        "runtime_failures": runtime_failures,
        "agreements": agreements,
        "no_agreements": no_agreements,
        "avg_convergence_round": avg_convergence,
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
        "--seed", type=str, default=SEED,
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
    records = collect_all(scenario_dir, args.seed)

    if not records:
        print("No scenarios found.", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    tel_path = write_telemetry(records, output_dir)
    index = build_index(records)
    idx_path = write_index(index, output_dir)

    print_summary(index)
    print(f"\n  telemetry → {tel_path}")
    print(f"  index     → {idx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
