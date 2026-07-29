"""
Scenario telemetry collector for HUB_Optimus.

Runs every scenario in a target directory through the simulator, captures
structured telemetry per execution, and writes:

  scenarios/telemetry.json   — array of per-scenario records
  scenarios/index.json       — aggregate statistics

Each telemetry record captures:
  scenario_id, family, actors, max_rounds, result_status,
  rounds_used, convergence_round, schema_valid, runtime_error,
  processing_outcome, error_code, and generation provenance

Usage:
  python tools/scenario_telemetry.py                          # default dirs
  python tools/scenario_telemetry.py --scenario-dir DIR       # custom input
  python tools/scenario_telemetry.py --manifest FILE          # manifested run
  python tools/scenario_telemetry.py --seed 99                # different seed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
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
MANIFEST_NAME = "generation_manifest.json"
MANIFEST_VERSION = 1
GENERATOR_ID = "tools/scenario_generator/generate_scenarios.py"
GENERATOR_FAMILIES = frozenset(
    {"info_asymmetry", "resource_scarcity", "incentive_misalignment"}
)


class ManifestError(ValueError):
    """Raised when a generation manifest cannot define a safe, verified run."""


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _manifest_run_id(payload: dict[str, Any]) -> str:
    descriptor = {
        "format_version": payload.get("format_version"),
        "generator": payload.get("generator"),
        "seed": payload.get("seed"),
        "requested_count": payload.get("requested_count"),
        "produced_count": payload.get("produced_count"),
        "files": payload.get("files"),
    }
    digest_input = json.dumps(
        descriptor, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(digest_input).hexdigest()}"


def load_manifest(
    scenario_dir: Path,
    manifest_path: Path,
) -> tuple[list[tuple[Path, str, bytes]], dict[str, Any]]:
    """Load a manifest and retain the exact bytes verified for each scenario."""
    root = scenario_dir.resolve()
    resolved_manifest = manifest_path.resolve()
    if resolved_manifest.parent != root:
        raise ManifestError(
            "manifest must be located directly in the scenario directory"
        )

    try:
        payload = json.loads(resolved_manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeError) as exc:
        raise ManifestError(f"cannot read manifest: {exc}") from exc

    if not isinstance(payload, dict):
        raise ManifestError("manifest root must be a JSON object")
    if payload.get("format_version") != MANIFEST_VERSION:
        raise ManifestError(
            f"unsupported manifest format_version: {payload.get('format_version')!r}"
        )
    if payload.get("generator") != GENERATOR_ID:
        raise ManifestError(
            f"unexpected manifest generator: {payload.get('generator')!r}"
        )
    seed = payload.get("seed")
    requested_count = payload.get("requested_count")
    produced_count = payload.get("produced_count")
    if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
        raise ManifestError("manifest seed must be an integer or null")
    if (
        not isinstance(requested_count, int)
        or isinstance(requested_count, bool)
        or requested_count < 0
    ):
        raise ManifestError("manifest requested_count must be a non-negative integer")
    if (
        not isinstance(produced_count, int)
        or isinstance(produced_count, bool)
        or produced_count < 0
    ):
        raise ManifestError("manifest produced_count must be a non-negative integer")
    if produced_count > requested_count:
        raise ManifestError("manifest produced_count exceeds requested_count")

    files = payload.get("files")
    if not isinstance(files, list):
        raise ManifestError("manifest files must be a list")
    if payload.get("produced_count") != len(files):
        raise ManifestError("manifest produced_count does not match files")
    if payload.get("run_id") != _manifest_run_id(payload):
        raise ManifestError("manifest run_id does not match its content")

    selected: list[tuple[Path, str, bytes]] = []
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise ManifestError("manifest file entries must be objects")
        relative = entry.get("path")
        expected_hash = entry.get("sha256")
        if (
            not isinstance(relative, str)
            or not isinstance(expected_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None
        ):
            raise ManifestError(
                "manifest file entries require a path and lowercase SHA-256"
            )
        pure = PurePosixPath(relative)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or pure.as_posix() != relative
            or len(pure.parts) != 2
            or pure.parts[0] not in GENERATOR_FAMILIES
            or not pure.stem.startswith(f"{pure.parts[0]}_")
            or not pure.stem.removeprefix(f"{pure.parts[0]}_").isdigit()
            or pure.suffix != ".json"
        ):
            raise ManifestError(f"unsafe manifest path: {relative!r}")
        if relative in seen:
            raise ManifestError(f"duplicate manifest path: {relative!r}")
        seen.add(relative)

        path = root.joinpath(*pure.parts)
        resolved = path.resolve()
        if not _is_relative_to(resolved, root):
            raise ManifestError(
                f"manifest path escapes scenario directory: {relative!r}"
            )
        if not path.is_file():
            raise ManifestError(f"manifest file not found: {relative!r}")
        try:
            scenario_bytes = path.read_bytes()
        except OSError as exc:
            raise ManifestError(f"cannot read manifest file {relative!r}: {exc}") from exc
        actual_hash = hashlib.sha256(scenario_bytes).hexdigest()
        if actual_hash != expected_hash:
            raise ManifestError(f"manifest hash mismatch: {relative!r}")
        selected.append((path, actual_hash, scenario_bytes))

    return selected, payload


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


def collect_one(
    scenario_path: Path,
    seed: int,
    *,
    generation_run_id: str | None = None,
    generation_seed: int | None = None,
    scenario_sha256: str | None = None,
    manifest_verified: bool = False,
    verified_scenario_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Run one scenario and return a telemetry record."""
    scenario_id = scenario_path.stem
    family = _infer_family(scenario_path)

    record: dict[str, Any] = {
        "scenario_id": scenario_id,
        "family": family,
        "mutation_axis": _infer_mutation_axis(scenario_path),
        "seed": seed,
        "generation_run_id": generation_run_id,
        "generation_seed": generation_seed,
        "scenario_sha256": scenario_sha256,
        "manifest_verified": manifest_verified,
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
        scenario_bytes = (
            verified_scenario_bytes
            if verified_scenario_bytes is not None
            else scenario_path.read_bytes()
        )
    except OSError:
        record["error_code"] = "read_error"
        return record

    try:
        payload = json.loads(scenario_bytes.decode("utf-8"))
    except UnicodeDecodeError:
        record["error_code"] = "invalid_utf8"
        return record
    except json.JSONDecodeError:
        record["error_code"] = "invalid_json"
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
    snapshot_directory: tempfile.TemporaryDirectory[str] | None = None
    runner_scenario_path = scenario_path
    actual: Path | None = None
    try:
        if verified_scenario_bytes is not None:
            snapshot_directory = tempfile.TemporaryDirectory(
                prefix="hub-optimus-telemetry-"
            )
            runner_scenario_path = (
                Path(snapshot_directory.name) / scenario_path.name
            )
            runner_scenario_path.write_bytes(verified_scenario_bytes)
        actual = runner_scenario_path.with_suffix(".telemetry_tmp.json")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [
                sys.executable, str(RUNNER),
                str(runner_scenario_path),
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
        if (
            not isinstance(rounds_used, int)
            or isinstance(rounds_used, bool)
            or rounds_used < 0
        ):
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
        if actual is not None:
            try:
                actual.unlink(missing_ok=True)
            except OSError:
                pass
        if snapshot_directory is not None:
            snapshot_directory.cleanup()

    return record


def collect_all(
    scenario_dir: Path,
    seed: int,
    manifest_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Collect telemetry for one manifested run or a legacy directory scan."""
    if manifest_path is not None:
        selected, manifest = load_manifest(scenario_dir, manifest_path)
        scenarios = [
            (
                path,
                file_hash,
                scenario_bytes,
                manifest["run_id"],
                manifest.get("seed"),
                True,
            )
            for path, file_hash, scenario_bytes in selected
        ]
    else:
        skip = {"telemetry.json", "index.json"}
        root_manifest = scenario_dir / MANIFEST_NAME
        scenarios = [
            (path, None, None, None, None, False)
            for path in sorted(
                p for p in scenario_dir.rglob("*.json")
                if p.name not in skip
                and p != root_manifest
                and ".telemetry_tmp" not in p.name
            )
        ]
    records: list[dict[str, Any]] = []

    for (
        path,
        file_hash,
        scenario_bytes,
        run_id,
        generation_seed,
        verified,
    ) in scenarios:
        record = collect_one(
            path,
            seed,
            generation_run_id=run_id,
            generation_seed=generation_seed,
            scenario_sha256=file_hash,
            manifest_verified=verified,
            verified_scenario_bytes=scenario_bytes,
        )
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

    run_ids = sorted(
        {
            r["generation_run_id"]
            for r in records
            if r.get("generation_run_id") is not None
        }
    )
    generation_seeds = sorted(
        {
            r["generation_seed"]
            for r in records
            if r.get("generation_seed") is not None
        }
    )
    manifest_verified = bool(records) and all(
        r.get("manifest_verified", False) for r in records
    )

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
        "generation": {
            "run_id": run_ids[0] if len(run_ids) == 1 else None,
            "seed": generation_seeds[0] if len(generation_seeds) == 1 else None,
            "manifest_verified": manifest_verified,
        },
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
        "--manifest",
        type=str,
        default=None,
        help=(
            f"Generation manifest to verify and select the current run "
            f"(auto-detected as {MANIFEST_NAME} in the scenario directory)."
        ),
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

    explicit_manifest = Path(args.manifest) if args.manifest else None
    if args.scenario_dir:
        scenario_dir = Path(args.scenario_dir)
    elif explicit_manifest is not None:
        scenario_dir = explicit_manifest.parent
    else:
        scenario_dir = DEFAULT_SCENARIO_DIR
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR

    if not scenario_dir.is_dir():
        print(f"Scenario directory not found: {scenario_dir}", file=sys.stderr)
        print("Run the generator first:\n"
              "  python tools/scenario_generator/generate_scenarios.py",
              file=sys.stderr)
        return 1

    manifest_path = explicit_manifest
    if manifest_path is None:
        candidate = scenario_dir / MANIFEST_NAME
        if candidate.is_file():
            manifest_path = candidate

    print(f"Collecting telemetry from {scenario_dir} ...\n")
    if manifest_path is None:
        print(
            "  Warning: no generation manifest; scanning legacy directory "
            "without generation-run provenance.\n",
            file=sys.stderr,
        )
    else:
        print(f"  Manifest: {manifest_path}\n")

    try:
        records = collect_all(scenario_dir, args.seed, manifest_path)
    except ManifestError as exc:
        print(f"[manifest-error] {exc}", file=sys.stderr)
        return 1
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
