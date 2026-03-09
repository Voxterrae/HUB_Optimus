"""
Scenario mutator for HUB_Optimus.

Takes a base scenario and produces controlled mutations along specific
axes, enabling stability boundary discovery.  Each mutation changes
exactly one parameter, so the effect is isolated and measurable.

Mutation axes
-------------
1. threshold  — vary success_criteria.offer (1 → 5)
2. rounds     — vary max_rounds (1 → 10)
3. actors     — add/remove negotiator actors (1 → 6)

Usage:
  python tools/scenario_mutator.py                                   # all axes, all families
  python tools/scenario_mutator.py --axis threshold                  # threshold sweep only
  python tools/scenario_mutator.py --base scenarios/generated/info_asymmetry/info_asymmetry_001.json
  python tools/scenario_mutator.py --output-dir DIR                  # custom output
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "scenario.schema.json"
GENERATED_DIR = REPO_ROOT / "scenarios" / "generated"
OUTPUT_DIR = REPO_ROOT / "scenarios" / "mutations"

EXTRA_ACTORS = [
    {"name": "Faction_E", "role": "negotiator"},
    {"name": "Faction_F", "role": "negotiator"},
    {"name": "Faction_G", "role": "negotiator"},
    {"name": "Faction_H", "role": "negotiator"},
    {"name": "Faction_I", "role": "negotiator"},
]


# ── Mutation functions ──────────────────────────────────────


def mutate_threshold(base: dict, base_label: str) -> list[tuple[str, dict]]:
    """Sweep success_criteria.offer from 1 to 5."""
    results = []
    for threshold in range(1, 6):
        m = copy.deepcopy(base)
        m["success_criteria"]["offer"] = threshold
        m["title"] = f"{base_label} [threshold={threshold}]"
        m["description"] = (
            f"Mutation of {base_label}: success threshold set to {threshold}. "
            f"Original: offer={base['success_criteria'].get('offer')}."
        )
        label = f"{base_label}_threshold_{threshold}"
        results.append((label, m))
    return results


def mutate_rounds(base: dict, base_label: str) -> list[tuple[str, dict]]:
    """Sweep max_rounds from 1 to 10."""
    results = []
    for rounds in range(1, 11):
        m = copy.deepcopy(base)
        m["max_rounds"] = rounds
        m["title"] = f"{base_label} [rounds={rounds}]"
        m["description"] = (
            f"Mutation of {base_label}: max_rounds set to {rounds}. "
            f"Original: max_rounds={base['max_rounds']}."
        )
        label = f"{base_label}_rounds_{rounds}"
        results.append((label, m))
    return results


def mutate_actors(base: dict, base_label: str) -> list[tuple[str, dict]]:
    """Sweep actor count from 1 to min(6, base+3) by adding/removing negotiators."""
    original_count = len(base["roles"])
    results = []

    for target in range(1, min(7, original_count + 4)):
        m = copy.deepcopy(base)
        if target < original_count:
            m["roles"] = m["roles"][:target]
        elif target > original_count:
            extra_needed = target - original_count
            m["roles"] = m["roles"] + EXTRA_ACTORS[:extra_needed]
        # target == original_count: keep as-is (control case)

        m["title"] = f"{base_label} [actors={target}]"
        m["description"] = (
            f"Mutation of {base_label}: actor count set to {target}. "
            f"Original: {original_count} actors."
        )
        label = f"{base_label}_actors_{target}"
        results.append((label, m))

    return results


AXES = {
    "threshold": mutate_threshold,
    "rounds": mutate_rounds,
    "actors": mutate_actors,
}


# ── Core logic ──────────────────────────────────────────────


def pick_base_scenarios(base_path: str | None) -> list[tuple[str, dict]]:
    """Select base scenario(s) for mutation.

    If base_path is given, use that single file.
    Otherwise pick one representative from each family.
    """
    if base_path:
        p = Path(base_path)
        payload = json.loads(p.read_text(encoding="utf-8"))
        return [(p.stem, payload)]

    bases = []
    if not GENERATED_DIR.is_dir():
        return bases

    for family_dir in sorted(GENERATED_DIR.iterdir()):
        if not family_dir.is_dir():
            continue
        # Pick the first scenario in each family as representative
        jsons = sorted(family_dir.glob("*.json"))
        if jsons:
            p = jsons[0]
            payload = json.loads(p.read_text(encoding="utf-8"))
            bases.append((p.stem, payload))

    return bases


def generate_mutations(
    bases: list[tuple[str, dict]],
    axes: list[str],
) -> list[tuple[str, str, dict]]:
    """Generate all mutations for the given bases and axes.

    Returns list of (filename_stem, axis_name, scenario_dict).
    """
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    results: list[tuple[str, str, dict]] = []

    for base_label, base_scenario in bases:
        for axis_name in axes:
            mutator = AXES[axis_name]
            mutations = mutator(base_scenario, base_label)
            for stem, scenario in mutations:
                errors = list(validator.iter_errors(scenario))
                if errors:
                    msgs = "; ".join(e.message for e in errors)
                    print(f"  SKIP  {stem}: schema invalid — {msgs}", file=sys.stderr)
                    continue
                results.append((stem, axis_name, scenario))

    return results


def write_mutations(
    mutations: list[tuple[str, str, dict]],
    output_dir: Path,
) -> int:
    """Write mutations organized by axis subdirectory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for stem, axis, scenario in mutations:
        axis_dir = output_dir / axis
        axis_dir.mkdir(parents=True, exist_ok=True)
        path = axis_dir / f"{stem}.json"
        path.write_text(
            json.dumps(scenario, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written += 1
    return written


# ── CLI ─────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate controlled scenario mutations for stability analysis."
    )
    parser.add_argument(
        "--base", type=str, default=None,
        help="Path to a single base scenario. Default: one per family.",
    )
    parser.add_argument(
        "--axis", type=str, default=None, choices=list(AXES.keys()),
        help="Mutation axis to sweep. Default: all axes.",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help=f"Output directory (default: {OUTPUT_DIR}).",
    )
    args = parser.parse_args()

    out = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    axes = [args.axis] if args.axis else list(AXES.keys())

    bases = pick_base_scenarios(args.base)
    if not bases:
        print("No base scenarios found. Run the generator first:\n"
              "  python tools/scenario_generator/generate_scenarios.py",
              file=sys.stderr)
        return 1

    print(f"Base scenarios: {len(bases)}")
    for label, _ in bases:
        print(f"  • {label}")
    print(f"Axes: {', '.join(axes)}\n")

    mutations = generate_mutations(bases, axes)
    written = write_mutations(mutations, out)

    print(f"\nGenerated {written} mutations in {out}")

    # Summary by axis
    axis_counts: dict[str, int] = {}
    for _, axis, _ in mutations:
        axis_counts[axis] = axis_counts.get(axis, 0) + 1
    for axis, count in sorted(axis_counts.items()):
        print(f"  {axis}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
