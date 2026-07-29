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
import shutil
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


def _write_staged_file(path: Path, content: bytes) -> None:
    """Write and flush one file inside a private transaction workspace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _publish_staged_file(staged: Path, target: Path) -> None:
    """Atomically publish one already-staged file."""
    os.replace(staged, target)


def _publish_transaction(
    root: Path,
    target_payloads: dict[str, bytes],
    manifest_content: bytes,
    *,
    stale_names: list[str],
    clean: bool,
) -> None:
    """Publish a complete generated set or restore the prior filesystem state."""
    workspace = Path(
        tempfile.mkdtemp(
            dir=root.parent,
            prefix=f".{root.name}.generation-",
        )
    )
    staged_root = workspace / "staged"
    backup_root = workspace / "backup"
    created_directories: list[Path] = []
    backups: list[tuple[Path, Path]] = []
    published: list[Path] = []

    try:
        for relative, content in sorted(target_payloads.items()):
            _write_staged_file(staged_root / relative, content)
        _write_staged_file(staged_root / MANIFEST_NAME, manifest_content)

        for family in sorted({relative.split("/", 1)[0] for relative in target_payloads}):
            family_dir = root / family
            _assert_safe_target(root, family_dir)
            if family_dir.exists():
                if not family_dir.is_dir():
                    raise UnsafeOutputError(
                        f"generator family path is not a directory: {family_dir}"
                    )
            else:
                family_dir.mkdir()
                created_directories.append(family_dir)

        backup_names = {
            relative
            for relative in target_payloads
            if (root / relative).exists()
        }
        if clean:
            backup_names.update(stale_names)
        manifest_path = root / MANIFEST_NAME
        if manifest_path.exists():
            backup_names.add(MANIFEST_NAME)

        for relative in sorted(backup_names):
            target = root / relative
            _assert_safe_target(root, target)
            if not target.is_file():
                raise UnsafeOutputError(
                    f"generator output target is not a regular file: {target}"
                )
            backup = backup_root / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, backup)
            backups.append((target, backup))

        for relative in sorted(target_payloads):
            target = root / relative
            _assert_safe_target(root, target)
            _publish_staged_file(staged_root / relative, target)
            published.append(target)

        _assert_safe_target(root, manifest_path)
        _publish_staged_file(staged_root / MANIFEST_NAME, manifest_path)
        published.append(manifest_path)
    except BaseException as exc:
        rollback_errors: list[OSError] = []
        for target in reversed(published):
            try:
                target.unlink(missing_ok=True)
            except OSError as rollback_error:
                rollback_errors.append(rollback_error)
        for target, backup in reversed(backups):
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(backup, target)
            except OSError as rollback_error:
                rollback_errors.append(rollback_error)
        for directory in reversed(created_directories):
            try:
                directory.rmdir()
            except OSError:
                pass
        if rollback_errors:
            raise OSError(
                "generation transaction failed and rollback was incomplete"
            ) from exc
        raise
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


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

    manifest_files: list[dict[str, str]] = []
    for relative in sorted(target_payloads):
        content = target_payloads[relative]
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
    manifest_content = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    _publish_transaction(
        root,
        target_payloads,
        manifest_content,
        stale_names=stale_names,
        clean=clean,
    )

    manifest_path = root / MANIFEST_NAME
    _assert_safe_target(root, manifest_path)

    return GenerationReport(
        run_id=manifest["run_id"],
        manifest_path=manifest_path,
        produced=produced,
        replaced=replaced,
        stale=tuple(stale_names),
        removed=tuple(stale_names if clean else ()),
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

    if args.count <= 0:
        print("[generator-error] --count must be greater than zero", file=sys.stderr)
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
