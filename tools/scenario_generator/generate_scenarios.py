"""
Synthetic scenario generator for HUB_Optimus.

Produces structurally valid negotiation scenarios from three template
families, validated against the canonical scenario.schema.json before
writing.  All randomness is seed-controlled for reproducibility.

Template families
-----------------
1. information_asymmetry  — actors with unequal leverage, variable thresholds
2. resource_scarcity      — tight rounds, high thresholds, failure-prone
3. incentive_misalignment — mixed roles (negotiator vs hardliner vs mediator)

Usage:
  python tools/scenario_generator/generate_scenarios.py             # 60 scenarios, seed 42
  python tools/scenario_generator/generate_scenarios.py --count 20  # 20 scenarios
  python tools/scenario_generator/generate_scenarios.py --seed 99   # different seed
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = REPO_ROOT / "scenario.schema.json"
OUTPUT_DIR = REPO_ROOT / "scenarios" / "generated"

# ── Actor and role pools ────────────────────────────────────

NEGOTIATOR_NAMES = [
    "Faction_A", "Faction_B", "Faction_C", "Faction_D",
    "Coalition_North", "Coalition_South", "Coalition_East",
    "Trade_Bloc", "Regional_Authority", "Observer_Mission",
]

MEDIATOR_NAMES = [
    "Mediator", "Envoy", "Arbiter", "Facilitator",
]

HARDLINER_NAMES = [
    "Hardliner_X", "Hardliner_Y", "Hardliner_Z",
]

# ── Template families ───────────────────────────────────────


def _info_asymmetry(rng: random.Random, index: int) -> dict:
    """Information asymmetry: 2-3 negotiators, moderate threshold, variable rounds."""
    n_actors = rng.choice([2, 3])
    actors = rng.sample(NEGOTIATOR_NAMES, n_actors)
    threshold = rng.choice([3, 4, 5])
    max_rounds = rng.randint(3, 7)
    return {
        "title": f"Information asymmetry scenario {index}",
        "description": (
            f"{n_actors} parties negotiate under unequal information. "
            f"Agreement threshold at {threshold}, up to {max_rounds} rounds."
        ),
        "roles": [{"name": a, "role": "negotiator"} for a in actors],
        "success_criteria": {"offer": threshold},
        "max_rounds": max_rounds,
    }


def _resource_scarcity(rng: random.Random, index: int) -> dict:
    """Resource scarcity: 2-4 actors, high threshold, tight rounds — failure-prone."""
    n_actors = rng.choice([2, 3, 4])
    actors = rng.sample(NEGOTIATOR_NAMES, n_actors)
    threshold = rng.choice([4, 5])
    max_rounds = rng.randint(1, 3)
    return {
        "title": f"Resource scarcity scenario {index}",
        "description": (
            f"{n_actors} parties compete for scarce resources. "
            f"High threshold ({threshold}) with only {max_rounds} round(s) "
            "creates pressure toward failure."
        ),
        "roles": [{"name": a, "role": "negotiator"} for a in actors],
        "success_criteria": {"offer": threshold},
        "max_rounds": max_rounds,
    }


def _incentive_misalignment(rng: random.Random, index: int) -> dict:
    """Incentive misalignment: mixed roles (negotiator + hardliner + optional mediator)."""
    n_negotiators = rng.choice([1, 2])
    n_hardliners = rng.choice([1, 2])
    has_mediator = rng.random() < 0.4

    actors_with_roles: list[dict] = []
    for name in rng.sample(NEGOTIATOR_NAMES, n_negotiators):
        actors_with_roles.append({"name": name, "role": "negotiator"})
    for name in rng.sample(HARDLINER_NAMES, n_hardliners):
        actors_with_roles.append({"name": name, "role": "hardliner"})
    if has_mediator:
        actors_with_roles.append(
            {"name": rng.choice(MEDIATOR_NAMES), "role": "mediator"}
        )

    threshold = rng.choice([3, 4, 5])
    max_rounds = rng.randint(2, 5)
    return {
        "title": f"Incentive misalignment scenario {index}",
        "description": (
            f"{len(actors_with_roles)} parties with conflicting incentives. "
            f"Mix of negotiators, hardliners"
            f"{' and mediator' if has_mediator else ''}. "
            f"Threshold {threshold}, {max_rounds} rounds."
        ),
        "roles": actors_with_roles,
        "success_criteria": {"offer": threshold},
        "max_rounds": max_rounds,
    }


FAMILIES = [
    ("info_asymmetry", _info_asymmetry),
    ("resource_scarcity", _resource_scarcity),
    ("incentive_misalignment", _incentive_misalignment),
]

# ── Core generation logic ───────────────────────────────────


def generate(count: int, seed: int) -> list[tuple[str, str, dict]]:
    """Generate *count* scenarios (evenly split across families).

    Returns a list of (filename_stem, family_name, scenario_dict) tuples.
    """
    rng = random.Random(seed)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    per_family = count // len(FAMILIES)
    remainder = count % len(FAMILIES)

    results: list[tuple[str, str, dict]] = []
    global_index = 0

    for family_index, (family_name, factory) in enumerate(FAMILIES):
        n = per_family + (1 if family_index < remainder else 0)
        for i in range(n):
            global_index += 1
            scenario = factory(rng, global_index)

            errors = list(validator.iter_errors(scenario))
            if errors:
                msgs = "; ".join(e.message for e in errors)
                print(
                    f"SKIP {family_name}_{global_index}: schema invalid — {msgs}",
                    file=sys.stderr,
                )
                continue

            stem = f"{family_name}_{global_index:03d}"
            results.append((stem, family_name, scenario))

    return results


def write_scenarios(scenarios: list[tuple[str, str, dict]], output_dir: Path) -> int:
    """Write scenarios to JSON files organised by family subdirectory.

    Returns the number of files written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for stem, family, scenario in scenarios:
        family_dir = output_dir / family
        family_dir.mkdir(parents=True, exist_ok=True)
        path = family_dir / f"{stem}.json"
        path.write_text(
            json.dumps(scenario, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written += 1
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic negotiation scenarios for HUB_Optimus."
    )
    parser.add_argument(
        "--count", type=int, default=60,
        help="Total number of scenarios to generate (default: 60).",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="RNG seed for reproducibility (default: 42).",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help=f"Output directory (default: {OUTPUT_DIR}).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.output_dir) if args.output_dir else OUTPUT_DIR

    scenarios = generate(args.count, args.seed)
    written = write_scenarios(scenarios, out)

    print(f"Generated {written} scenarios in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
