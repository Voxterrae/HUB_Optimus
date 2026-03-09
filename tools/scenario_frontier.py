"""
Two-axis stability frontier mapping for HUB_Optimus.

Probes the full grid for pairs of axes, producing stability matrices
that show the exact shape of the stable/unstable boundary surface.

Planes mapped
-------------
- actors × rounds          — decouples actor count from round budget
- threshold × rounds       — decouples threshold from round budget

Output
------
- scenarios/frontiers/<plane>_seed_<N>.json   — per-seed matrices
- stdout summary with ASCII heatmaps

Usage:
  python tools/scenario_frontier.py
  python tools/scenario_frontier.py --seed 99
  python tools/scenario_frontier.py --seeds 1,42,123
  python tools/scenario_frontier.py --plane actors_rounds
  python tools/scenario_frontier.py --plane threshold_rounds
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import scenario_boundary_search
from scenario_boundary_search import (
    EXTRA_ACTORS,
    OUTPUT_DIR,
    pick_base_scenarios,
    probe_detail,
    set_actors,
    set_rounds,
    set_threshold,
)

FRONTIERS_DIR = OUTPUT_DIR / "frontiers"

# Axis ranges
ROUNDS_RANGE = range(1, 11)
ACTORS_RANGE = range(1, 7)
THRESHOLD_RANGE = range(1, 6)


# ── Grid probing ───────────────────────────────────────────


def probe_grid(
    base: dict,
    row_name: str,
    row_range: range,
    col_name: str,
    col_range: range,
    seed: str,
) -> dict:
    """Probe a 2D grid and return a matrix of results.

    Each cell is {"status": "success"|"failure", "rounds": N|null}.
    """
    matrix: dict = {}
    for row_val in row_range:
        row_key = str(row_val)
        matrix[row_key] = {}
        for col_val in col_range:
            col_key = str(col_val)
            scenario = mutate_two(base, row_name, row_val, col_name, col_val)
            detail = probe_detail(scenario, seed)
            matrix[row_key][col_key] = detail
    return matrix


def mutate_two(base: dict, axis1: str, val1: int, axis2: str, val2: int) -> dict:
    """Apply two mutations sequentially."""
    s = _apply_one(base, axis1, val1)
    return _apply_one(s, axis2, val2)


def _apply_one(base: dict, axis: str, value: int) -> dict:
    if axis == "actors":
        return set_actors(base, value)
    if axis == "rounds":
        return set_rounds(base, value)
    if axis == "threshold":
        return set_threshold(base, value)
    raise ValueError(f"Unknown axis: {axis}")


# ── Plane definitions ──────────────────────────────────────


PLANES = {
    "actors_rounds": {
        "row_name": "actors",
        "row_range": ACTORS_RANGE,
        "col_name": "rounds",
        "col_range": ROUNDS_RANGE,
    },
    "threshold_rounds": {
        "row_name": "threshold",
        "row_range": THRESHOLD_RANGE,
        "col_name": "rounds",
        "col_range": ROUNDS_RANGE,
    },
}


# ── Core ───────────────────────────────────────────────────


def map_plane(
    plane_name: str,
    bases: list[tuple[str, str, dict]],
    seed: str,
) -> dict:
    """Map a 2D plane for all families. Returns per-family matrices."""
    plane = PLANES[plane_name]
    result: dict = {"plane": plane_name, "seed": int(seed), "families": {}}
    total_probes = len(plane["row_range"]) * len(plane["col_range"])

    for _stem, family, scenario in bases:
        print(f"\n  {family} ({total_probes} probes)")
        matrix = probe_grid(
            scenario,
            plane["row_name"],
            plane["row_range"],
            plane["col_name"],
            plane["col_range"],
            seed,
        )
        result["families"][family] = {
            "base_scenario": _stem,
            "matrix": matrix,
        }

    return result


# ── Output ─────────────────────────────────────────────────


def write_frontier(data: dict, plane_name: str, seed: str) -> Path:
    FRONTIERS_DIR.mkdir(parents=True, exist_ok=True)
    path = FRONTIERS_DIR / f"{plane_name}_seed_{seed}.json"
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def print_heatmap(data: dict) -> None:
    """Print ASCII stability heatmaps."""
    plane_name = data["plane"]
    plane = PLANES[plane_name]
    seed = data["seed"]

    print(f"\n{'=' * 60}")
    print(f"  Stability frontier: {plane_name} (seed {seed})")
    print(f"{'=' * 60}")

    for family in sorted(data["families"]):
        matrix = data["families"][family]["matrix"]
        print(f"\n  {family}")

        # Header
        col_range = plane["col_range"]
        row_name = plane["row_name"]
        col_name = plane["col_name"]
        header = f"  {row_name:>10s} \\ {col_name:<6s}"
        for c in col_range:
            header += f" {c:>4d}"
        print(header)
        print("  " + "-" * (len(header) - 2))

        # Rows
        for r in plane["row_range"]:
            row_key = str(r)
            line = f"  {r:>10d}  |"
            for c in col_range:
                col_key = str(c)
                cell = matrix.get(row_key, {}).get(col_key, {})
                status = cell.get("status", "error")
                conv_round = cell.get("rounds")
                if status == "success":
                    line += f"  R{conv_round}"
                else:
                    line += "   X"
            print(line)

    print(f"\n{'=' * 60}")


def summarize_frontiers(all_data: list[dict]) -> dict:
    """Extract stability region summaries from frontier data."""
    summaries: dict = {}

    for data in all_data:
        plane_name = data["plane"]
        seed = str(data["seed"])
        plane = PLANES[plane_name]

        for family in data["families"]:
            if family not in summaries:
                summaries[family] = {}
            if plane_name not in summaries[family]:
                summaries[family][plane_name] = {}

            matrix = data["families"][family]["matrix"]
            stable_cells = 0
            total_cells = 0
            # Find the stability boundary contour
            boundary_points: list[tuple[int, int]] = []

            for r in plane["row_range"]:
                for c in plane["col_range"]:
                    cell = matrix[str(r)][str(c)]
                    total_cells += 1
                    if cell["status"] == "success":
                        stable_cells += 1
                        # Check if this is a boundary cell (adjacent to failure)
                        is_boundary = False
                        if r > plane["row_range"][0]:
                            prev = matrix[str(r - 1)][str(c)]
                            if prev["status"] != "success":
                                is_boundary = True
                        else:
                            is_boundary = True
                        if c > plane["col_range"][0]:
                            prev = matrix[str(r)][str(c - 1)]
                            if prev["status"] != "success":
                                is_boundary = True
                        if is_boundary:
                            boundary_points.append((r, c))

            summaries[family][plane_name][seed] = {
                "stable_cells": stable_cells,
                "total_cells": total_cells,
                "stability_ratio": round(stable_cells / total_cells, 3),
                "boundary_points": boundary_points,
            }

    return summaries


# ── CLI ────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Map two-axis stability frontiers."
    )
    parser.add_argument(
        "--seed", type=str, default="42",
        help="Seed for reproducible runs (default: 42).",
    )
    parser.add_argument(
        "--seeds", type=str, default=None,
        help="Comma-separated seeds for multi-seed mapping.",
    )
    parser.add_argument(
        "--plane", type=str, default=None,
        choices=list(PLANES.keys()),
        help="Map a specific plane only (default: both).",
    )
    parser.add_argument(
        "--policy", type=str, default=None,
        help="Negotiation policy name (e.g. uniform, biased).",
    )
    args = parser.parse_args()

    scenario_boundary_search.ACTIVE_POLICY = args.policy

    bases = pick_base_scenarios()
    if not bases:
        print(
            "No base scenarios found. Run the generator first:\n"
            "  python tools/scenario_generator/generate_scenarios.py",
            file=sys.stderr,
        )
        return 1

    seeds = [s.strip() for s in args.seeds.split(",")] if args.seeds else [args.seed]
    planes = [args.plane] if args.plane else list(PLANES.keys())

    print("Two-axis stability frontier mapping")
    print(f"  Families: {len(bases)}")
    print(f"  Seeds: {', '.join(seeds)}")
    print(f"  Planes: {', '.join(planes)}")

    all_data: list[dict] = []

    for plane_name in planes:
        for seed in seeds:
            print(f"\n{'=' * 40}")
            print(f"  Plane: {plane_name}  |  Seed: {seed}")
            print(f"{'=' * 40}")

            data = map_plane(plane_name, bases, seed)
            out = write_frontier(data, plane_name, seed)
            print_heatmap(data)
            print(f"\n  -> {out}")
            all_data.append(data)

    # Print stability summaries
    summaries = summarize_frontiers(all_data)
    print(f"\n{'=' * 60}")
    print("  Stability region summaries")
    print(f"{'=' * 60}")
    for family in sorted(summaries):
        print(f"\n  {family}")
        for plane_name in sorted(summaries[family]):
            print(f"    {plane_name}:")
            for seed in sorted(summaries[family][plane_name]):
                s = summaries[family][plane_name][seed]
                bp = s["boundary_points"]
                bp_str = ", ".join(f"({r},{c})" for r, c in bp[:6])
                if len(bp) > 6:
                    bp_str += " ..."
                print(
                    f"      seed {seed}: {s['stable_cells']}/{s['total_cells']} "
                    f"stable ({s['stability_ratio']:.1%}), "
                    f"boundary: [{bp_str}]"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
