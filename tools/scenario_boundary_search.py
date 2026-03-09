"""
Boundary search for HUB_Optimus scenarios.

Uses binary search to find the exact stability boundary for each
parameter axis on each scenario family.  Instead of sweeping the full
range (like the mutator), this finds the minimum stable value with
O(log N) probes per axis.

Axes searched
-------------
- rounds_min  — minimum max_rounds for agreement
- actors_min  — minimum actor count for agreement
- threshold_max — maximum success_criteria.offer that still converges

Output
------
- scenarios/boundaries.json — per-family boundary map
- stdout summary

Usage:
  python tools/scenario_boundary_search.py
  python tools/scenario_boundary_search.py --seed 99
  python tools/scenario_boundary_search.py --seeds 42,99,7
  python tools/scenario_boundary_search.py --verify
  python tools/scenario_boundary_search.py --gradient
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "run_scenario.py"
SCHEMA_PATH = REPO_ROOT / "scenario.schema.json"
GENERATED_DIR = REPO_ROOT / "scenarios" / "generated"
OUTPUT_DIR = REPO_ROOT / "scenarios"

EXTRA_ACTORS = [
    {"name": "Faction_E", "role": "negotiator"},
    {"name": "Faction_F", "role": "negotiator"},
    {"name": "Faction_G", "role": "negotiator"},
    {"name": "Faction_H", "role": "negotiator"},
    {"name": "Faction_I", "role": "negotiator"},
]


# ── Probe ───────────────────────────────────────────────────


def probe(scenario: dict, seed: str) -> bool:
    """Run a scenario once and return True if agreement is reached."""
    with tempfile.TemporaryDirectory() as tmp:
        scenario_path = Path(tmp) / "probe.json"
        result_path = Path(tmp) / "result.json"

        scenario_path.write_text(
            json.dumps(scenario, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [
                sys.executable, str(RUNNER),
                str(scenario_path),
                "--output", str(result_path),
                "--seed", seed,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )

        if proc.returncode != 0:
            return False

        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
            return result.get("status") == "success"
        except (json.JSONDecodeError, OSError):
            return False


def probe_detail(scenario: dict, seed: str) -> dict:
    """Run a scenario and return status + convergence round."""
    with tempfile.TemporaryDirectory() as tmp:
        scenario_path = Path(tmp) / "probe.json"
        result_path = Path(tmp) / "result.json"

        scenario_path.write_text(
            json.dumps(scenario, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [
                sys.executable, str(RUNNER),
                str(scenario_path),
                "--output", str(result_path),
                "--seed", seed,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )

        if proc.returncode != 0:
            return {"status": "error", "rounds": None}

        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
            return {
                "status": result.get("status", "error"),
                "rounds": result.get("rounds"),
            }
        except (json.JSONDecodeError, OSError):
            return {"status": "error", "rounds": None}


# ── Mutation helpers ────────────────────────────────────────


def set_rounds(base: dict, value: int) -> dict:
    m = copy.deepcopy(base)
    m["max_rounds"] = value
    return m


def set_actors(base: dict, value: int) -> dict:
    m = copy.deepcopy(base)
    original = len(base["roles"])
    if value < original:
        m["roles"] = m["roles"][:value]
    elif value > original:
        m["roles"] = m["roles"] + EXTRA_ACTORS[: value - original]
    return m


def set_threshold(base: dict, value: int) -> dict:
    m = copy.deepcopy(base)
    m["success_criteria"]["offer"] = value
    return m


# ── Binary search ───────────────────────────────────────────


def find_min_stable(base: dict, mutate_fn, lo: int, hi: int, seed: str) -> int | None:
    """Find minimum value in [lo, hi] where the scenario converges.

    Returns the boundary value, or None if no stable point exists.
    """
    # First check: does the highest value work?
    if not probe(mutate_fn(base, hi), seed):
        return None

    # Binary search: lo = last known failure, hi = last known success
    # Find the smallest value that succeeds
    fail = lo - 1
    succeed = hi

    # Check lo directly
    if probe(mutate_fn(base, lo), seed):
        return lo

    fail = lo

    while succeed - fail > 1:
        mid = (fail + succeed) // 2
        if probe(mutate_fn(base, mid), seed):
            succeed = mid
        else:
            fail = mid

    return succeed


def find_max_stable(base: dict, mutate_fn, lo: int, hi: int, seed: str) -> int | None:
    """Find maximum value in [lo, hi] where the scenario converges.

    Returns the boundary value, or None if no stable point exists.
    """
    # First check: does the lowest value work?
    if not probe(mutate_fn(base, lo), seed):
        return None

    # Binary search for the highest succeeding value
    succeed = lo
    fail = hi + 1

    # Check hi directly
    if probe(mutate_fn(base, hi), seed):
        return hi

    fail = hi

    while fail - succeed > 1:
        mid = (succeed + fail) // 2
        if probe(mutate_fn(base, mid), seed):
            succeed = mid
        else:
            fail = mid

    return succeed


# ── Boundary verification ──────────────────────────────────


def verify_boundary_min(
    base: dict, mutate_fn, boundary: int, lo: int, seed: str
) -> dict:
    """Verify a minimum boundary: boundary-1 should fail, boundary should succeed."""
    at_boundary = probe(mutate_fn(base, boundary), seed)
    below = boundary > lo and not probe(mutate_fn(base, boundary - 1), seed)
    # If boundary == lo, there's nothing below to test
    if boundary <= lo:
        below = True  # trivially valid — no lower value to test
    return {
        "boundary": boundary,
        "at_boundary": at_boundary,
        "below_fails": below,
        "valid": at_boundary and below,
    }


def verify_boundary_max(
    base: dict, mutate_fn, boundary: int, hi: int, seed: str
) -> dict:
    """Verify a maximum boundary: boundary should succeed, boundary+1 should fail."""
    at_boundary = probe(mutate_fn(base, boundary), seed)
    above = boundary < hi and not probe(mutate_fn(base, boundary + 1), seed)
    if boundary >= hi:
        above = True  # trivially valid — no higher value to test
    return {
        "boundary": boundary,
        "at_boundary": at_boundary,
        "above_fails": above,
        "valid": at_boundary and above,
    }


def verify_boundaries(
    bases: list[tuple[str, str, dict]],
    boundaries: dict,
    seed: str,
) -> dict:
    """Verify all boundaries in a result set. Returns verification report."""
    report: dict = {}
    for _stem, family, scenario in bases:
        if family not in boundaries:
            continue
        entry = boundaries[family]
        v: dict = {}

        rounds_min = entry.get("rounds_min")
        if rounds_min is not None:
            print(f"    {family} rounds_min={rounds_min} ...", end=" ", flush=True)
            r = verify_boundary_min(scenario, set_rounds, rounds_min, 1, seed)
            v["rounds_min"] = r
            print("ok" if r["valid"] else "FAIL")

        actors_min = entry.get("actors_min")
        if actors_min is not None:
            print(f"    {family} actors_min={actors_min} ...", end=" ", flush=True)
            r = verify_boundary_min(scenario, set_actors, actors_min, 1, seed)
            v["actors_min"] = r
            print("ok" if r["valid"] else "FAIL")

        threshold_max = entry.get("threshold_max")
        if threshold_max is not None:
            print(f"    {family} threshold_max={threshold_max} ...", end=" ", flush=True)
            r = verify_boundary_max(scenario, set_threshold, threshold_max, 5, seed)
            v["threshold_max"] = r
            print("ok" if r["valid"] else "FAIL")

        report[family] = v
    return report


# ── Convergence gradient ───────────────────────────────────


def measure_gradient(
    bases: list[tuple[str, str, dict]], seed: str
) -> dict:
    """Measure convergence round at each parameter value to produce gradient curves.

    Returns per-family curves: parameter value → convergence round (or null).
    """
    gradients: dict = {}

    for _stem, family, scenario in bases:
        print(f"\n  {family}")
        fam: dict = {}

        # rounds gradient: max_rounds 1–10
        print("    rounds 1-10 ...", end=" ", flush=True)
        rounds_curve: dict = {}
        for r in range(1, 11):
            detail = probe_detail(set_rounds(scenario, r), seed)
            if detail["status"] == "success":
                rounds_curve[str(r)] = detail["rounds"]
            else:
                rounds_curve[str(r)] = None
        print("done")
        fam["rounds"] = rounds_curve

        # actors gradient: actor count 1–6
        print("    actors 1-6 ...", end=" ", flush=True)
        actors_curve: dict = {}
        for a in range(1, 7):
            detail = probe_detail(set_actors(scenario, a), seed)
            if detail["status"] == "success":
                actors_curve[str(a)] = detail["rounds"]
            else:
                actors_curve[str(a)] = None
        print("done")
        fam["actors"] = actors_curve

        # threshold gradient: offer 1–5
        print("    threshold 1-5 ...", end=" ", flush=True)
        threshold_curve: dict = {}
        for t in range(1, 6):
            detail = probe_detail(set_threshold(scenario, t), seed)
            if detail["status"] == "success":
                threshold_curve[str(t)] = detail["rounds"]
            else:
                threshold_curve[str(t)] = None
        print("done")
        fam["threshold"] = threshold_curve

        gradients[family] = {"seed": int(seed), "curves": fam}

    return gradients


# ── Core logic ──────────────────────────────────────────────


def pick_base_scenarios() -> list[tuple[str, str, dict]]:
    """Select one representative base scenario per family.

    Returns list of (stem, family_name, scenario_dict).
    """
    bases = []
    if not GENERATED_DIR.is_dir():
        return bases

    for family_dir in sorted(GENERATED_DIR.iterdir()):
        if not family_dir.is_dir():
            continue
        jsons = sorted(family_dir.glob("*.json"))
        if jsons:
            p = jsons[0]
            payload = json.loads(p.read_text(encoding="utf-8"))
            bases.append((p.stem, family_dir.name, payload))

    return bases


def search_boundaries(
    bases: list[tuple[str, str, dict]], seed: str
) -> dict:
    """Run boundary search on all families and return results."""
    boundaries: dict = {}

    for stem, family, scenario in bases:
        print(f"\n  {family} ({stem})")
        entry: dict = {"base_scenario": stem, "seed": int(seed)}

        # rounds: find minimum stable (range 1–10)
        print("    rounds ...", end=" ", flush=True)
        rounds_min = find_min_stable(scenario, set_rounds, 1, 10, seed)
        entry["rounds_min"] = rounds_min
        print(rounds_min)

        # actors: find minimum stable (range 1–6)
        print("    actors ...", end=" ", flush=True)
        actors_min = find_min_stable(scenario, set_actors, 1, 6, seed)
        entry["actors_min"] = actors_min
        print(actors_min)

        # threshold: find maximum viable (range 1–5)
        print("    threshold ...", end=" ", flush=True)
        threshold_max = find_max_stable(scenario, set_threshold, 1, 5, seed)
        entry["threshold_max"] = threshold_max
        print(threshold_max)

        boundaries[family] = entry

    return boundaries


def search_multi_seed(
    bases: list[tuple[str, str, dict]], seeds: list[str]
) -> dict:
    """Run boundary search across multiple seeds and report consensus."""
    all_results: dict = {}

    for seed in seeds:
        print(f"\n{'=' * 40}")
        print(f"  Seed: {seed}")
        print(f"{'=' * 40}")
        result = search_boundaries(bases, seed)
        all_results[seed] = result

    # Build consensus: for each family, take the worst case (highest min, lowest max)
    consensus: dict = {}
    families = {f for r in all_results.values() for f in r}

    for family in sorted(families):
        rounds_vals = [
            all_results[s][family]["rounds_min"]
            for s in seeds
            if family in all_results[s] and all_results[s][family]["rounds_min"] is not None
        ]
        actors_vals = [
            all_results[s][family]["actors_min"]
            for s in seeds
            if family in all_results[s] and all_results[s][family]["actors_min"] is not None
        ]
        threshold_vals = [
            all_results[s][family]["threshold_max"]
            for s in seeds
            if family in all_results[s] and all_results[s][family]["threshold_max"] is not None
        ]

        consensus[family] = {
            "rounds_min": max(rounds_vals) if rounds_vals else None,
            "actors_min": max(actors_vals) if actors_vals else None,
            "threshold_max": min(threshold_vals) if threshold_vals else None,
            "seeds_tested": len(seeds),
            "per_seed": {
                s: all_results[s][family] for s in seeds if family in all_results[s]
            },
        }

    return consensus


# ── Output ──────────────────────────────────────────────────


def write_boundaries(boundaries: dict, output_dir: Path) -> Path:
    path = output_dir / "boundaries.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(boundaries, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def print_summary(boundaries: dict) -> None:
    print(f"\n{'=' * 50}")
    print("  Stability Boundaries")
    print(f"{'=' * 50}")

    for family in sorted(boundaries):
        entry = boundaries[family]
        print(f"\n  {family}")

        if "per_seed" in entry:
            # Multi-seed consensus
            print(f"    rounds_min:    {entry['rounds_min']}  (worst-case across {entry['seeds_tested']} seeds)")
            print(f"    actors_min:    {entry['actors_min']}  (worst-case)")
            print(f"    threshold_max: {entry['threshold_max']}  (worst-case)")
        else:
            print(f"    rounds_min:    {entry['rounds_min']}")
            print(f"    actors_min:    {entry['actors_min']}")
            print(f"    threshold_max: {entry['threshold_max']}")

    print(f"\n{'=' * 50}")


# ── CLI ─────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find stability boundaries via binary search."
    )
    parser.add_argument(
        "--seed", type=str, default="42",
        help="Seed for reproducible runs (default: 42).",
    )
    parser.add_argument(
        "--seeds", type=str, default=None,
        help="Comma-separated seeds for multi-seed consensus (e.g. 42,99,7).",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="After searching, verify each boundary (boundary passes, boundary-1 fails).",
    )
    parser.add_argument(
        "--gradient", action="store_true",
        help="Measure convergence round at each parameter value (convergence curves).",
    )
    args = parser.parse_args()

    bases = pick_base_scenarios()
    if not bases:
        print(
            "No base scenarios found. Run the generator first:\n"
            "  python tools/scenario_generator/generate_scenarios.py",
            file=sys.stderr,
        )
        return 1

    print("Boundary search")
    print(f"  Families: {len(bases)}")
    for stem, family, _ in bases:
        print(f"    {family} ({stem})")

    if args.seeds:
        seeds = [s.strip() for s in args.seeds.split(",")]
        boundaries = search_multi_seed(bases, seeds)
    else:
        boundaries = search_boundaries(bases, args.seed)

    out = write_boundaries(boundaries, OUTPUT_DIR)
    print_summary(boundaries)
    print(f"\n  boundaries -> {out}")

    # Verification pass
    if args.verify:
        if args.seeds:
            # Multi-seed: verify each seed's OWN boundaries
            seeds = [s.strip() for s in args.seeds.split(",")]
            all_valid = True
            full_report: dict = {}
            for seed in seeds:
                print(f"\n{'=' * 50}")
                print(f"  Verifying boundaries (seed {seed})")
                print(f"{'=' * 50}")
                per_seed_boundaries = {}
                for fam, entry in boundaries.items():
                    ps = entry.get("per_seed", {})
                    if seed in ps:
                        per_seed_boundaries[fam] = ps[seed]
                if per_seed_boundaries:
                    report = verify_boundaries(bases, per_seed_boundaries, seed)
                    full_report[seed] = report
                    for fam_report in report.values():
                        for v in fam_report.values():
                            if not v["valid"]:
                                all_valid = False
            print(f"\n  Verification: {'ALL PASSED' if all_valid else 'SOME FAILED'}")
            for fam in boundaries:
                boundaries[fam]["verification"] = {
                    s: full_report[s].get(fam, {})
                    for s in full_report
                    if fam in full_report[s]
                }
        else:
            seed = args.seed
            print(f"\n{'=' * 50}")
            print(f"  Verifying boundaries (seed {seed})")
            print(f"{'=' * 50}")
            verify_target = {}
            for fam, entry in boundaries.items():
                verify_target[fam] = {
                    "rounds_min": entry.get("rounds_min"),
                    "actors_min": entry.get("actors_min"),
                    "threshold_max": entry.get("threshold_max"),
                }
            report = verify_boundaries(bases, verify_target, seed)
            all_valid = all(
                v["valid"]
                for fam_report in report.values()
                for v in fam_report.values()
            )
            print(f"\n  Verification: {'ALL PASSED' if all_valid else 'SOME FAILED'}")
            for fam in report:
                if fam in boundaries:
                    boundaries[fam]["verification"] = report[fam]
        write_boundaries(boundaries, OUTPUT_DIR)

    # Convergence gradient
    if args.gradient:
        seed = args.seed
        print(f"\n{'=' * 50}")
        print(f"  Convergence gradient (seed {seed})")
        print(f"{'=' * 50}")
        gradients = measure_gradient(bases, seed)
        # Print gradient summary
        for family in sorted(gradients):
            curves = gradients[family]["curves"]
            print(f"\n  {family}")
            for axis in ("rounds", "actors", "threshold"):
                curve = curves[axis]
                vals = [f"{k}:{curve[k] if curve[k] is not None else 'X'}" for k in curve]
                print(f"    {axis}: {', '.join(vals)}")
        # Merge gradients into output
        for fam in gradients:
            if fam in boundaries:
                boundaries[fam]["gradient"] = gradients[fam]
        write_boundaries(boundaries, OUTPUT_DIR)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
