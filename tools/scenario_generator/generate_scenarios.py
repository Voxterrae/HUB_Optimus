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
  python tools/scenario_generator/generate_scenarios.py --count 20 --clean
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = REPO_ROOT / "scenario.schema.json"
OUTPUT_DIR = REPO_ROOT / "scenarios" / "generated"
MANIFEST_NAME = "generation_manifest.json"
MANIFEST_VERSION = 1
GENERATOR_ID = "tools/scenario_generator/generate_scenarios.py"

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
FAMILY_NAMES = frozenset(name for name, _factory in FAMILIES)

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


class UnsafeOutputError(ValueError):
    """Raised when an output path escapes the declared generation root."""


@dataclass(frozen=True)
class GenerationReport:
    """Summary of one content-addressed generation run."""

    run_id: str
    manifest_path: Path
    produced: tuple[str, ...]
    replaced: tuple[str, ...]
    stale: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def written(self) -> int:
        return len(self.produced) + len(self.replaced)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolved_output_root(output_dir: Path) -> Path:
    """Create and resolve the exact root owned by this invocation."""
    if output_dir.is_symlink():
        raise UnsafeOutputError(
            f"refusing symlink output directory: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    root = output_dir.resolve()
    if root == Path(root.anchor):
        raise UnsafeOutputError("refusing to use a filesystem root as output directory")
    return root


def _assert_safe_target(root: Path, target: Path) -> None:
    """Reject symlinks and any target resolving outside *root*."""
    if target.is_symlink():
        raise UnsafeOutputError(f"refusing symlink output target: {target}")
    resolved = target.resolve(strict=False)
    if not _is_relative_to(resolved, root):
        raise UnsafeOutputError(f"output target escapes declared directory: {target}")


def _generator_owned_files(root: Path) -> dict[str, Path]:
    """Return files in the generator's exact, documented namespace.

    Only immediate ``<family>/<family>_<digits>.json`` paths are owned.
    Other JSON files and nested content are user data and are never removed.
    """
    owned: dict[str, Path] = {}
    for family in sorted(FAMILY_NAMES):
        family_dir = root / family
        if not family_dir.exists():
            continue
        _assert_safe_target(root, family_dir)
        if not family_dir.is_dir():
            raise UnsafeOutputError(f"generator family path is not a directory: {family_dir}")

        pattern = re.compile(rf"{re.escape(family)}_\d+\.json")
        for path in family_dir.iterdir():
            if not pattern.fullmatch(path.name):
                continue
            _assert_safe_target(root, path)
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                owned[relative] = path
    return owned


def _serialized_scenario(scenario: dict) -> bytes:
    return (
        json.dumps(scenario, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    """Replace one generated file atomically within its existing directory."""
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _manifest_payload(
    *,
    seed: int | None,
    requested_count: int,
    files: list[dict[str, str]],
) -> dict:
    descriptor = {
        "format_version": MANIFEST_VERSION,
        "generator": GENERATOR_ID,
        "seed": seed,
        "requested_count": requested_count,
        "produced_count": len(files),
        "files": files,
    }
    digest_input = json.dumps(
        descriptor, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return {
        **descriptor,
        "run_id": f"sha256:{hashlib.sha256(digest_input).hexdigest()}",
    }


def write_generation(
    scenarios: list[tuple[str, str, dict]],
    output_dir: Path,
    *,
    seed: int | None,
    requested_count: int,
    clean: bool = False,
) -> GenerationReport:
    """Write a manifested scenario set under an explicit output root.

    Generator ownership is limited to the exact family/filename namespace
    returned by :func:`_generator_owned_files`.  ``--clean`` removes only
    stale files in that namespace and never removes other content.
    """
    root = _resolved_output_root(output_dir)
    existing = _generator_owned_files(root)
    target_payloads: dict[str, bytes] = {}

    for stem, family, scenario in scenarios:
        if family not in FAMILY_NAMES:
            raise UnsafeOutputError(f"unknown generator family: {family}")
        if not re.fullmatch(rf"{re.escape(family)}_\d+", stem):
            raise UnsafeOutputError(f"invalid generator-owned scenario stem: {stem}")
        relative = (Path(family) / f"{stem}.json").as_posix()
        target_payloads[relative] = _serialized_scenario(scenario)

    target_names = set(target_payloads)
    stale_names = sorted(set(existing) - target_names)
    produced = tuple(sorted(target_names - set(existing)))
    replaced = tuple(sorted(target_names & set(existing)))
    removed: list[str] = []

    if clean:
        for relative in stale_names:
            path = existing[relative]
            _assert_safe_target(root, path)
            path.unlink()
            removed.append(relative)

    manifest_files: list[dict[str, str]] = []
    for relative in sorted(target_payloads):
        family, filename = relative.split("/", 1)
        family_dir = output_dir / family
        family_dir.mkdir(parents=True, exist_ok=True)
        _assert_safe_target(root, family_dir)
        path = family_dir / filename
        _assert_safe_target(root, path)
        content = target_payloads[relative]
        _atomic_write(path, content)
        manifest_files.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )

    manifest = _manifest_payload(
        seed=seed,
        requested_count=requested_count,
        files=manifest_files,
    )
    manifest_path = output_dir / MANIFEST_NAME
    _assert_safe_target(root, manifest_path)
    _atomic_write(
        manifest_path,
        (
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8"),
    )

    return GenerationReport(
        run_id=manifest["run_id"],
        manifest_path=manifest_path,
        produced=produced,
        replaced=replaced,
        stale=tuple(stale_names),
        removed=tuple(removed),
    )


def write_scenarios(scenarios: list[tuple[str, str, dict]], output_dir: Path) -> int:
    """Compatibility wrapper that now also writes a current-set manifest."""
    report = write_generation(
        scenarios,
        output_dir,
        seed=None,
        requested_count=len(scenarios),
    )
    return report.written


def _print_paths(label: str, paths: tuple[str, ...]) -> None:
    print(f"{label} ({len(paths)}):")
    for path in paths:
        print(f"  {path}")


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
    parser.add_argument(
        "--clean",
        action="store_true",
        help=(
            "Remove stale files only from the generator-owned family/filename "
            "namespace inside the resolved output directory."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.output_dir) if args.output_dir else OUTPUT_DIR

    if args.count < 0:
        print("[generator-error] --count must be zero or greater", file=sys.stderr)
        return 2

    scenarios = generate(args.count, args.seed)
    try:
        report = write_generation(
            scenarios,
            out,
            seed=args.seed,
            requested_count=args.count,
            clean=args.clean,
        )
    except (OSError, UnsafeOutputError) as exc:
        print(f"[generator-error] {exc}", file=sys.stderr)
        return 1

    print(f"Generation run: {report.run_id}")
    print(f"Generated {report.written} scenarios in {out}")
    _print_paths("Produced", report.produced)
    _print_paths("Replaced", report.replaced)
    if args.clean:
        _print_paths("Stale removed", report.removed)
    else:
        _print_paths("Stale retained (not current in manifest)", report.stale)
    print(f"Manifest: {report.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
