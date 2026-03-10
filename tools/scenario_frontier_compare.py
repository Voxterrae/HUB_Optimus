"""
Comparative frontier analysis between negotiation policies.

Runs the same two-axis stability frontiers under two different policies
and computes structural differences: stable area, frontier shift,
and average convergence round delta.

Output
------
- scenarios/frontiers/comparisons/<policyA>_vs_<policyB>_seed_<N>.json
- stdout comparison tables

Usage:
  python tools/scenario_frontier_compare.py --policy-a uniform --policy-b biased
  python tools/scenario_frontier_compare.py --policy-a uniform --policy-b biased --seeds 1,42,123
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import scenario_boundary_search
from scenario_boundary_search import pick_base_scenarios
from scenario_frontier import (
    FRONTIERS_DIR,
    PLANES,
    map_plane,
    print_heatmap,
    write_frontier,
)

COMPARISONS_DIR = FRONTIERS_DIR / "comparisons"


# ── Comparison metrics ─────────────────────────────────────


def compare_matrices(
    matrix_a: dict,
    matrix_b: dict,
    plane: dict,
) -> dict:
    """Compare two frontier matrices and return structural metrics."""
    stable_a = 0
    stable_b = 0
    total = 0
    round_sum_a = 0.0
    round_sum_b = 0.0
    round_count_a = 0
    round_count_b = 0

    # Per-row: find the minimum column that is stable (boundary)
    min_col_a: dict[int, int | None] = {}
    min_col_b: dict[int, int | None] = {}

    for r in plane["row_range"]:
        rk = str(r)
        min_col_a[r] = None
        min_col_b[r] = None
        for c in plane["col_range"]:
            ck = str(c)
            total += 1
            cell_a = matrix_a.get(rk, {}).get(ck, {})
            cell_b = matrix_b.get(rk, {}).get(ck, {})

            if cell_a.get("status") == "success":
                stable_a += 1
                rounds_a = cell_a.get("rounds")
                if rounds_a is not None:
                    round_sum_a += rounds_a
                    round_count_a += 1
                if min_col_a[r] is None:
                    min_col_a[r] = c

            if cell_b.get("status") == "success":
                stable_b += 1
                rounds_b = cell_b.get("rounds")
                if rounds_b is not None:
                    round_sum_b += rounds_b
                    round_count_b += 1
                if min_col_b[r] is None:
                    min_col_b[r] = c

    avg_round_a = round(round_sum_a / round_count_a, 2) if round_count_a else None
    avg_round_b = round(round_sum_b / round_count_b, 2) if round_count_b else None
    avg_round_delta = None
    if avg_round_a is not None and avg_round_b is not None:
        avg_round_delta = round(avg_round_b - avg_round_a, 2)

    # Frontier shift: compare the minimum stable column per row
    frontier_shifts: list[dict] = []
    for r in plane["row_range"]:
        ca = min_col_a[r]
        cb = min_col_b[r]
        if ca is not None and cb is not None:
            frontier_shifts.append({
                "row": r,
                "boundary_a": ca,
                "boundary_b": cb,
                "shift": cb - ca,
            })
        elif ca is None and cb is not None:
            frontier_shifts.append({
                "row": r,
                "boundary_a": None,
                "boundary_b": cb,
                "shift": "new_stable",
            })
        elif ca is not None and cb is None:
            frontier_shifts.append({
                "row": r,
                "boundary_a": ca,
                "boundary_b": None,
                "shift": "lost_stable",
            })

    return {
        "stable_area_a": stable_a,
        "stable_area_b": stable_b,
        "stable_area_delta": stable_b - stable_a,
        "total_cells": total,
        "stability_ratio_a": round(stable_a / total, 3) if total else 0,
        "stability_ratio_b": round(stable_b / total, 3) if total else 0,
        "avg_round_a": avg_round_a,
        "avg_round_b": avg_round_b,
        "avg_round_delta": avg_round_delta,
        "frontier_shifts": frontier_shifts,
    }


def compare_frontiers(
    data_a: dict,
    data_b: dict,
    policy_a: str,
    policy_b: str,
) -> dict:
    """Compare two frontier datasets across all families and return comparison."""
    plane_name = data_a["plane"]
    seed = data_a["seed"]
    plane = PLANES[plane_name]

    comparison: dict = {
        "plane": plane_name,
        "seed": seed,
        "policy_a": policy_a,
        "policy_b": policy_b,
        "families": {},
    }

    families_a = data_a.get("families", {})
    families_b = data_b.get("families", {})

    for family in sorted(set(families_a) | set(families_b)):
        if family not in families_a or family not in families_b:
            continue
        matrix_a = families_a[family]["matrix"]
        matrix_b = families_b[family]["matrix"]
        metrics = compare_matrices(matrix_a, matrix_b, plane)
        comparison["families"][family] = metrics

    return comparison


# ── Output ─────────────────────────────────────────────────


def write_comparison(data: dict, policy_a: str, policy_b: str, seed: str) -> Path:
    COMPARISONS_DIR.mkdir(parents=True, exist_ok=True)
    plane = data["plane"]
    path = COMPARISONS_DIR / f"{policy_a}_vs_{policy_b}_{plane}_seed_{seed}.json"
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def print_comparison(comparison: dict) -> None:
    """Print a human-readable comparison summary."""
    plane = comparison["plane"]
    seed = comparison["seed"]
    pa = comparison["policy_a"]
    pb = comparison["policy_b"]

    print(f"\n{'=' * 60}")
    print(f"  Policy comparison: {pa} vs {pb}")
    print(f"  Plane: {plane}  |  Seed: {seed}")
    print(f"{'=' * 60}")

    for family in sorted(comparison["families"]):
        m = comparison["families"][family]
        print(f"\n  {family}")
        print(f"    stable area {pa}: {m['stable_area_a']}/{m['total_cells']} ({m['stability_ratio_a']:.1%})")
        print(f"    stable area {pb}: {m['stable_area_b']}/{m['total_cells']} ({m['stability_ratio_b']:.1%})")
        delta = m["stable_area_delta"]
        sign = "+" if delta > 0 else ""
        print(f"    Δ stable area: {sign}{delta}")

        if m["avg_round_a"] is not None and m["avg_round_b"] is not None:
            rd = m["avg_round_delta"]
            rsign = "+" if rd > 0 else ""
            print(f"    avg convergence round {pa}: {m['avg_round_a']}")
            print(f"    avg convergence round {pb}: {m['avg_round_b']}")
            print(f"    Δ avg round: {rsign}{rd}")

        # Frontier shift summary
        shifts = m.get("frontier_shifts", [])
        structural_shifts = [s for s in shifts if isinstance(s["shift"], int) and s["shift"] != 0]
        new_stable = [s for s in shifts if s["shift"] == "new_stable"]
        lost_stable = [s for s in shifts if s["shift"] == "lost_stable"]

        if structural_shifts:
            print(f"    frontier shifts: {len(structural_shifts)} rows changed")
            for s in structural_shifts:
                row_name = PLANES[plane]["row_name"]
                col_name = PLANES[plane]["col_name"]
                ssign = "+" if s["shift"] > 0 else ""
                print(f"      {row_name}={s['row']}: {col_name}_min {s['boundary_a']}→{s['boundary_b']} ({ssign}{s['shift']})")
        if new_stable:
            print(f"    newly stable rows under {pb}: {len(new_stable)}")
            for s in new_stable:
                row_name = PLANES[plane]["row_name"]
                print(f"      {row_name}={s['row']}: was all-fail, now stable at {PLANES[plane]['col_name']}={s['boundary_b']}")
        if lost_stable:
            print(f"    lost stability under {pb}: {len(lost_stable)}")
        if not structural_shifts and not new_stable and not lost_stable:
            print("    frontier shifts: none (identical boundary)")


def print_cross_seed_summary(all_comparisons: list[dict]) -> None:
    """Print aggregate summary across seeds."""
    pa = all_comparisons[0]["policy_a"]
    pb = all_comparisons[0]["policy_b"]

    # Gather per-family, per-plane, per-seed metrics
    agg: dict = {}
    for comp in all_comparisons:
        plane = comp["plane"]
        seed = comp["seed"]
        for family, m in comp["families"].items():
            key = (family, plane)
            if key not in agg:
                agg[key] = {"deltas": [], "round_deltas": [], "seeds": []}
            agg[key]["deltas"].append(m["stable_area_delta"])
            if m["avg_round_delta"] is not None:
                agg[key]["round_deltas"].append(m["avg_round_delta"])
            agg[key]["seeds"].append(str(seed))

    print(f"\n{'=' * 60}")
    print(f"  Cross-seed summary: {pa} vs {pb}")
    print(f"{'=' * 60}")

    for (family, plane), v in sorted(agg.items()):
        deltas = v["deltas"]
        rd = v["round_deltas"]
        avg_delta = round(sum(deltas) / len(deltas), 1) if deltas else 0
        min_d = min(deltas) if deltas else 0
        max_d = max(deltas) if deltas else 0
        avg_rd = round(sum(rd) / len(rd), 2) if rd else None

        sign = "+" if avg_delta > 0 else ""
        print(f"\n  {family} ({plane})")
        print(f"    seeds: {', '.join(v['seeds'])}")
        print(f"    Δ stable area: min={min_d}, max={max_d}, avg={sign}{avg_delta}")
        if avg_rd is not None:
            rsign = "+" if avg_rd > 0 else ""
            print(f"    Δ avg round: avg={rsign}{avg_rd}")

        # Seed variance
        if len(deltas) > 1:
            mean = sum(deltas) / len(deltas)
            variance = sum((d - mean) ** 2 for d in deltas) / len(deltas)
            print(f"    seed variance (Δ area): {variance:.1f}")

    print(f"\n{'=' * 60}")


# ── CLI ────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare stability frontiers across two negotiation policies."
    )
    parser.add_argument(
        "--policy-a", type=str, required=True,
        help="First policy name (e.g. uniform).",
    )
    parser.add_argument(
        "--policy-b", type=str, required=True,
        help="Second policy name (e.g. biased).",
    )
    parser.add_argument(
        "--seeds", type=str, default="42",
        help="Comma-separated seeds (default: 42).",
    )
    parser.add_argument(
        "--plane", type=str, default=None,
        choices=list(PLANES.keys()),
        help="Compare a specific plane only (default: both).",
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

    seeds = [s.strip() for s in args.seeds.split(",")]
    planes = [args.plane] if args.plane else list(PLANES.keys())
    policy_a = args.policy_a
    policy_b = args.policy_b

    print(f"Comparative frontier analysis: {policy_a} vs {policy_b}")
    print(f"  Families: {len(bases)}")
    print(f"  Seeds: {', '.join(seeds)}")
    print(f"  Planes: {', '.join(planes)}")

    all_comparisons: list[dict] = []

    for plane_name in planes:
        for seed in seeds:
            print(f"\n{'=' * 40}")
            print(f"  Plane: {plane_name}  |  Seed: {seed}")
            print(f"{'=' * 40}")

            # Run frontier for policy A
            print(f"\n  --- {policy_a} ---")
            scenario_boundary_search.ACTIVE_POLICY = policy_a
            data_a = map_plane(plane_name, bases, seed)
            print_heatmap(data_a)

            # Run frontier for policy B
            print(f"\n  --- {policy_b} ---")
            scenario_boundary_search.ACTIVE_POLICY = policy_b
            data_b = map_plane(plane_name, bases, seed)
            print_heatmap(data_b)

            # Compare
            comparison = compare_frontiers(data_a, data_b, policy_a, policy_b)
            out = write_comparison(comparison, policy_a, policy_b, seed)
            print_comparison(comparison)
            print(f"\n  -> {out}")
            all_comparisons.append(comparison)

    # Cross-seed summary
    if len(seeds) > 1:
        print_cross_seed_summary(all_comparisons)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
