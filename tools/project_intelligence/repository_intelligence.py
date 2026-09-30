#!/usr/bin/env python3
"""Generate deterministic repository inventory and intelligence delta artifacts.

The generator reads only versioned Git objects and the evidence-bound Project Intelligence
model. It never treats source presence as proof of mutable deployment state and it does not
rewrite the semantic model automatically.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

INVENTORY_SCHEMA = "hub-optimus-project-intelligence.inventory.v1.1"
DELTA_SCHEMA = "hub-optimus-project-intelligence.delta.v1.1"
DEFAULT_MODEL = "site/obsidian-HUB_Optimus/system.json"
DEFAULT_INVENTORY = "site/obsidian-HUB_Optimus/system.inventory.json"
DEFAULT_DELTA = "site/obsidian-HUB_Optimus/system.delta.json"
GENERATOR_PATH = "tools/project_intelligence/repository_intelligence.py"
GENERATED_PATHS = frozenset({DEFAULT_INVENTORY, DEFAULT_DELTA})
MODEL_SECTIONS = (
    "components",
    "external_systems",
    "dependencies",
    "interfaces",
    "entities",
    "deployment",
)
NODE_SECTIONS = frozenset({"components", "external_systems", "dependencies"})
ARCHITECTURE_SUFFIXES = frozenset(
    {
        ".css",
        ".html",
        ".ini",
        ".js",
        ".json",
        ".md",
        ".ps1",
        ".py",
        ".sh",
        ".toml",
        ".ts",
        ".tsx",
        ".yaml",
        ".yml",
    }
)


@dataclass(frozen=True)
class GitObject:
    path: str
    mode: str
    object_type: str
    object_id: str
    size: int | None


@dataclass(frozen=True)
class SourceRule:
    object_ref: str
    section: str
    object_id: str
    object_name: str
    source: str
    prefix: bool


def run_git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )
    if process.returncode != 0:
        command = " ".join(["git", *args])
        raise RuntimeError(f"{command} failed: {process.stderr.strip()}")
    return process.stdout


def resolve_commit(root: Path, reference: str) -> str:
    return run_git(root, "rev-parse", "--verify", f"{reference}^{{commit}}").strip()


def resolve_tree(root: Path, commit: str) -> str:
    return run_git(root, "rev-parse", "--verify", f"{commit}^{{tree}}").strip()


def commit_time(root: Path, commit: str) -> str:
    return run_git(root, "show", "-s", "--format=%cI", commit).strip()


def commit_distance(root: Path, baseline: str, current: str) -> int:
    return int(run_git(root, "rev-list", "--count", f"{baseline}..{current}").strip())


def list_git_objects(root: Path, commit: str) -> list[GitObject]:
    output = run_git(root, "ls-tree", "-r", "-l", "--full-tree", commit)
    objects: list[GitObject] = []
    for raw_line in output.splitlines():
        if not raw_line:
            continue
        metadata, path = raw_line.split("\t", 1)
        mode, object_type, object_id, raw_size = metadata.split(maxsplit=3)
        size = None if raw_size == "-" else int(raw_size)
        if path in GENERATED_PATHS:
            continue
        objects.append(
            GitObject(
                path=path,
                mode=mode,
                object_type=object_type,
                object_id=object_id,
                size=size,
            )
        )
    return sorted(objects, key=lambda item: item.path)


def load_json_at_commit(root: Path, commit: str, path: str) -> dict[str, Any]:
    payload = run_git(root, "show", f"{commit}:{path}")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object at {commit}")
    return value


def load_model(root: Path, commit: str, model_path: str) -> dict[str, Any]:
    core = load_json_at_commit(root, commit, model_path)
    model = dict(core)
    model_dir = PurePosixPath(model_path).parent
    for reference in core.get("includes", []):
        if not isinstance(reference, str):
            raise ValueError(f"Invalid model include: {reference!r}")
        include_path = str(model_dir / reference)
        fragment = load_json_at_commit(root, commit, include_path)
        model.update(fragment)
    return model


def normalize_source(source: str) -> str:
    normalized = source.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def build_source_rules(model: dict[str, Any], paths: set[str]) -> list[SourceRule]:
    rules: list[SourceRule] = []
    for section in MODEL_SECTIONS:
        for item in model.get(section, []):
            if not isinstance(item, dict) or not item.get("id"):
                continue
            object_id = str(item["id"])
            object_name = str(item.get("name", object_id))
            object_ref = f"{section}:{object_id}"
            for raw_source in item.get("source", []):
                if not isinstance(raw_source, str):
                    continue
                source = normalize_source(raw_source)
                if not source:
                    continue
                prefix = raw_source.rstrip().endswith("/")
                if not prefix and source not in paths:
                    prefix = any(path.startswith(f"{source}/") for path in paths)
                rules.append(
                    SourceRule(
                        object_ref=object_ref,
                        section=section,
                        object_id=object_id,
                        object_name=object_name,
                        source=source,
                        prefix=prefix,
                    )
                )
    return sorted(rules, key=lambda rule: (rule.source, rule.object_ref))


def rules_for_path(path: str, rules: Sequence[SourceRule]) -> list[SourceRule]:
    matches = [
        rule
        for rule in rules
        if path == rule.source or (rule.prefix and path.startswith(f"{rule.source}/"))
    ]
    return sorted(matches, key=lambda rule: rule.object_ref)


def classify_domain(path: str) -> tuple[str, str]:
    """Return a deterministic path-domain label and its evidence level."""

    if path.startswith("site/obsidian-HUB_Optimus/") or path.startswith(
        "obsidian-HUB_Optimus/"
    ) or path.startswith("tools/project_intelligence/") or path.startswith(
        "tests/test_project_intelligence"
    ):
        return "project-intelligence", "CONFIRMED"
    if path.startswith("site/operator/"):
        return "operator", "CONFIRMED"
    if path.startswith(".github/workflows/") or path.startswith(".github/scripts/"):
        return "github-automation", "CONFIRMED"
    if path.startswith("docs/governance/") or path.startswith("config/governance/") or path in {
        ".github/CODEOWNERS",
        "AGENTS.md",
        "KERNEL_CHARTER.md",
        "KERNEL_CHARTER_EN.md",
    }:
        return "governance", "CONFIRMED"
    if path.startswith("semantic_engine/"):
        return "semantic-engine", "CONFIRMED"
    if path.startswith("ops/"):
        return "operations-infrastructure", "CONFIRMED"
    if path.startswith("tests/"):
        return "tests", "CONFIRMED"
    if path.startswith("benchmarks/") or path.startswith("tools/scenario") or path in {
        "hub_optimus_simulator.py",
        "run_scenario.py",
        "scenario.schema.json",
    }:
        return "scenario-laboratory", "CONFIRMED"
    if path.startswith("site/"):
        return "public-site", "CONFIRMED"
    if path.startswith("docs/") or path.lower().endswith(".md"):
        return "documentation", "CONFIRMED"
    if path.startswith("config/") or PurePosixPath(path).name in {
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        ".yamllint",
    }:
        return "configuration", "CONFIRMED"
    if path.startswith("hub_optimus/"):
        return "prototype-runtime", "CONFIRMED"
    return "other", "INFERRED"


def architecture_candidate(path: str, domain: str) -> tuple[bool, str | None]:
    suffix = PurePosixPath(path).suffix.lower()
    name = PurePosixPath(path).name
    if domain in {
        "project-intelligence",
        "operator",
        "github-automation",
        "governance",
        "semantic-engine",
        "operations-infrastructure",
        "scenario-laboratory",
        "public-site",
        "prototype-runtime",
    }:
        return True, f"domain:{domain}"
    if suffix in ARCHITECTURE_SUFFIXES and (
        "/" not in path
        or path.startswith(("config/", "docs/", "tests/"))
        or name.startswith(("README", "SECURITY", "CONTRIBUTING"))
    ):
        return True, f"suffix:{suffix or '[none]'}"
    return False, None


def source_rule_payload(rule: SourceRule) -> dict[str, Any]:
    return {
        "object": rule.object_ref,
        "name": rule.object_name,
        "section": rule.section,
        "source": rule.source,
        "match": "prefix" if rule.prefix else "exact",
    }


def build_inventory(
    root: Path,
    current_commit: str,
    model_path: str = DEFAULT_MODEL,
) -> tuple[dict[str, Any], dict[str, GitObject], list[SourceRule]]:
    current_tree = resolve_tree(root, current_commit)
    objects = list_git_objects(root, current_commit)
    object_map = {item.path: item for item in objects}
    paths = set(object_map)
    model = load_model(root, current_commit, model_path)
    rules = build_source_rules(model, paths)

    domain_counts: Counter[str] = Counter()
    domain_bytes: Counter[str] = Counter()
    mapped_paths: set[str] = set()
    file_entries: list[dict[str, Any]] = []
    unmapped_candidates: list[dict[str, Any]] = []

    for item in objects:
        domain, domain_confidence = classify_domain(item.path)
        domain_counts[domain] += 1
        domain_bytes[domain] += item.size or 0
        matches = rules_for_path(item.path, rules)
        if matches:
            mapped_paths.add(item.path)
        candidate, candidate_reason = architecture_candidate(item.path, domain)
        entry = {
            "path": item.path,
            "mode": item.mode,
            "object_type": item.object_type,
            "git_object": item.object_id,
            "bytes": item.size,
            "domain": domain,
            "domain_confidence": domain_confidence,
            "architecture_candidate": candidate,
            "candidate_reason": candidate_reason,
            "model_objects": [rule.object_ref for rule in matches],
        }
        file_entries.append(entry)
        if candidate and not matches:
            unmapped_candidates.append(
                {
                    "path": item.path,
                    "domain": domain,
                    "reason": candidate_reason,
                    "confidence": "INFERRED",
                    "review_state": "candidate",
                }
            )

    unresolved_sources: list[dict[str, Any]] = []
    for rule in rules:
        resolved = any(
            path == rule.source or (rule.prefix and path.startswith(f"{rule.source}/"))
            for path in paths
        )
        if not resolved:
            unresolved_sources.append(source_rule_payload(rule))

    total_files = len(objects)
    mapped_files = len(mapped_paths)
    coverage_ratio = round(mapped_files / total_files, 6) if total_files else 0.0
    domains = [
        {
            "id": domain,
            "files": domain_counts[domain],
            "bytes": domain_bytes[domain],
            "classification_confidence": "CONFIRMED" if domain != "other" else "INFERRED",
        }
        for domain in sorted(domain_counts)
    ]

    inventory = {
        "schema_version": INVENTORY_SCHEMA,
        "repository": {
            "name": model.get("analysis", {}).get("repository", "Voxterrae/HUB_Optimus"),
            "commit": current_commit,
            "tree": current_tree,
            "commit_time": commit_time(root, current_commit),
            "semantic_baseline_commit": model.get("analysis", {}).get("commit"),
            "semantic_baseline_tree": model.get("analysis", {}).get("tree"),
        },
        "generation": {
            "generator": GENERATOR_PATH,
            "deterministic": True,
            "tracked_git_objects_only": True,
            "excluded_generated_paths": sorted(GENERATED_PATHS),
            "boundary": (
                "The inventory confirms versioned Git objects and deterministic path mappings; "
                "domain classification or architecture relevance may be INFERRED and mutable "
                "external state is not inspected."
            ),
        },
        "summary": {
            "tracked_files": total_files,
            "tracked_bytes": sum(item.size or 0 for item in objects),
            "domains": len(domains),
            "mapped_files": mapped_files,
            "unmapped_files": total_files - mapped_files,
            "source_coverage_ratio": coverage_ratio,
            "architecture_candidates": sum(
                1 for item in file_entries if item["architecture_candidate"]
            ),
            "unmapped_architecture_candidates": len(unmapped_candidates),
            "unresolved_model_sources": len(unresolved_sources),
        },
        "domains": domains,
        "model_source_rules": [source_rule_payload(rule) for rule in rules],
        "unresolved_model_sources": unresolved_sources,
        "unmapped_architecture_candidates": sorted(
            unmapped_candidates, key=lambda item: item["path"]
        ),
        "files": file_entries,
    }
    return inventory, object_map, rules


def parse_name_status(output: str) -> list[tuple[str, str | None, str]]:
    changes: list[tuple[str, str | None, str]] = []
    for raw_line in output.splitlines():
        if not raw_line:
            continue
        fields = raw_line.split("\t")
        status = fields[0]
        if status.startswith(("R", "C")):
            if len(fields) != 3:
                raise ValueError(f"Unexpected rename/copy record: {raw_line!r}")
            changes.append((status, fields[1], fields[2]))
        else:
            if len(fields) != 2:
                raise ValueError(f"Unexpected change record: {raw_line!r}")
            changes.append((status, None, fields[1]))
    return changes


def node_impact(model: dict[str, Any], direct_nodes: set[str]) -> dict[str, list[str]]:
    forward: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    for relation in model.get("relations", []):
        source = str(relation.get("from", ""))
        target = str(relation.get("to", ""))
        if not source or not target:
            continue
        forward[source].add(target)
        reverse[target].add(source)

    def traverse(graph: dict[str, set[str]]) -> set[str]:
        visited = set(direct_nodes)
        queue: deque[str] = deque(sorted(direct_nodes))
        while queue:
            current = queue.popleft()
            for neighbour in sorted(graph.get(current, set())):
                if neighbour in visited:
                    continue
                visited.add(neighbour)
                queue.append(neighbour)
        return visited - direct_nodes

    return {
        "direct_nodes": sorted(direct_nodes),
        "upstream_nodes": sorted(traverse(reverse)),
        "downstream_nodes": sorted(traverse(forward)),
    }


def build_delta(
    root: Path,
    baseline_commit: str,
    current_commit: str,
    inventory: dict[str, Any],
    current_objects: dict[str, GitObject],
    rules: Sequence[SourceRule],
    model_path: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    baseline_objects = {item.path: item for item in list_git_objects(root, baseline_commit)}
    model = load_model(root, current_commit, model_path)
    raw_changes = run_git(
        root,
        "diff",
        "--name-status",
        "--find-renames",
        baseline_commit,
        current_commit,
    )
    parsed = parse_name_status(raw_changes)

    change_entries: list[dict[str, Any]] = []
    direct_node_ids: set[str] = set()
    changed_domains: Counter[str] = Counter()
    unmodelled_architecture_changes: list[dict[str, Any]] = []

    inventory_files = {item["path"]: item for item in inventory.get("files", [])}
    for status, old_path, path in parsed:
        domain, domain_confidence = classify_domain(path)
        changed_domains[domain] += 1
        matches = rules_for_path(path, rules)
        if old_path:
            matches = sorted(
                {rule.object_ref: rule for rule in [*matches, *rules_for_path(old_path, rules)]}.values(),
                key=lambda rule: rule.object_ref,
            )
        model_objects = [rule.object_ref for rule in matches]
        for rule in matches:
            if rule.section in NODE_SECTIONS:
                direct_node_ids.add(rule.object_id)

        current_item = current_objects.get(path)
        baseline_item = baseline_objects.get(old_path or path)
        candidate_source = inventory_files.get(path)
        candidate = bool(candidate_source and candidate_source.get("architecture_candidate"))
        if not candidate and status.startswith("D"):
            candidate, reason = architecture_candidate(path, domain)
        else:
            reason = candidate_source.get("candidate_reason") if candidate_source else None

        change_entries.append(
            {
                "status": status,
                "path": path,
                "old_path": old_path,
                "domain": domain,
                "domain_confidence": domain_confidence,
                "baseline_git_object": baseline_item.object_id if baseline_item else None,
                "current_git_object": current_item.object_id if current_item else None,
                "architecture_candidate": candidate,
                "model_objects": model_objects,
                "review_state": "requires-review" if candidate else "recorded",
            }
        )
        if candidate and not model_objects:
            unmodelled_architecture_changes.append(
                {
                    "path": path,
                    "status": status,
                    "domain": domain,
                    "reason": reason,
                    "confidence": "INFERRED",
                    "review_state": "requires-review",
                }
            )

    impact = node_impact(model, direct_node_ids)
    drift_candidates: list[dict[str, Any]] = []
    if baseline_commit != current_commit:
        drift_candidates.append(
            {
                "id": "semantic-baseline-behind-current-tree",
                "kind": "freshness",
                "status": "active",
                "confidence": "CONFIRMED",
                "claim": "The repository commit analyzed by the semantic model differs from the current analyzed commit.",
                "evidence": [baseline_commit, current_commit],
                "review_state": "requires-review",
            }
        )
    if inventory.get("unresolved_model_sources"):
        drift_candidates.append(
            {
                "id": "unresolved-model-source-references",
                "kind": "source-drift",
                "status": "active",
                "confidence": "CONFIRMED",
                "claim": "One or more model source references do not resolve in the current analyzed tree.",
                "evidence": [
                    item["source"] for item in inventory["unresolved_model_sources"]
                ],
                "review_state": "requires-review",
            }
        )
    if unmodelled_architecture_changes:
        drift_candidates.append(
            {
                "id": "changed-unmodelled-architecture-candidates",
                "kind": "coverage-drift",
                "status": "partial",
                "confidence": "INFERRED",
                "claim": "Architecture-relevant changed paths exist without an explicit model source mapping.",
                "evidence": [item["path"] for item in unmodelled_architecture_changes],
                "review_state": "requires-review",
            }
        )

    status_counts = Counter(item["status"][0] for item in change_entries)
    return {
        "schema_version": DELTA_SCHEMA,
        "repository": inventory["repository"]["name"],
        "comparison": {
            "from_commit": baseline_commit,
            "from_tree": resolve_tree(root, baseline_commit),
            "to_commit": current_commit,
            "to_tree": resolve_tree(root, current_commit),
            "to_commit_time": commit_time(root, current_commit),
            "commit_distance": commit_distance(root, baseline_commit, current_commit),
        },
        "generation": {
            "generator": GENERATOR_PATH,
            "deterministic": True,
            "boundary": (
                "The delta identifies changed evidence and impact candidates. It does not "
                "automatically rewrite architectural facts or certify mutable external state."
            ),
        },
        "summary": {
            "changed_paths": len(change_entries),
            "added": status_counts.get("A", 0),
            "modified": status_counts.get("M", 0),
            "deleted": status_counts.get("D", 0),
            "renamed_or_copied": status_counts.get("R", 0) + status_counts.get("C", 0),
            "changed_domains": len(changed_domains),
            "directly_impacted_nodes": len(impact["direct_nodes"]),
            "upstream_nodes": len(impact["upstream_nodes"]),
            "downstream_nodes": len(impact["downstream_nodes"]),
            "unmodelled_architecture_changes": len(unmodelled_architecture_changes),
            "drift_candidates": len(drift_candidates),
        },
        "changed_domains": [
            {"id": domain, "changed_paths": changed_domains[domain]}
            for domain in sorted(changed_domains)
        ],
        "impact": impact,
        "unmodelled_architecture_changes": sorted(
            unmodelled_architecture_changes, key=lambda item: item["path"]
        ),
        "drift_candidates": drift_candidates,
        "changes": sorted(change_entries, key=lambda item: (item["path"], item["status"])),
        "review_boundary": {
            "automatic_fact_updates": False,
            "human_review_required": True,
            "live_external_state": "UNKNOWN",
            "next_step": (
                "Review changed evidence, resolve coverage and drift candidates, then update "
                "only affected JSON facts, Obsidian notes, views and tests."
            ),
        },
    }


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def write_or_check(path: Path, content: str, check: bool) -> bool:
    if check:
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            print(f"OUT_OF_DATE: {path}", file=sys.stderr)
            return False
        print(f"OK: {path}")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"WROTE: {path}")
    return True


def existing_inventory_commit(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    commit = payload.get("repository", {}).get("commit")
    return commit if isinstance(commit, str) and len(commit) == 40 else None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--current", default=None)
    parser.add_argument("--inventory-out", default=DEFAULT_INVENTORY)
    parser.add_argument("--delta-out", default=DEFAULT_DELTA)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    inventory_path = root / args.inventory_out
    delta_path = root / args.delta_out

    requested_current = args.current
    if requested_current is None and args.check:
        requested_current = existing_inventory_commit(inventory_path)
    current_commit = resolve_commit(root, requested_current or "HEAD")

    model = load_model(root, current_commit, args.model)
    baseline_reference = args.baseline or model.get("analysis", {}).get("commit")
    if not isinstance(baseline_reference, str) or not baseline_reference:
        raise ValueError("No semantic baseline commit is available")
    baseline_commit = resolve_commit(root, baseline_reference)

    inventory, current_objects, rules = build_inventory(root, current_commit, args.model)
    delta = build_delta(
        root,
        baseline_commit,
        current_commit,
        inventory,
        current_objects,
        rules,
        args.model,
    )

    ok_inventory = write_or_check(inventory_path, canonical_json(inventory), args.check)
    ok_delta = write_or_check(delta_path, canonical_json(delta), args.check)
    return 0 if ok_inventory and ok_delta else 1


if __name__ == "__main__":
    raise SystemExit(main())
