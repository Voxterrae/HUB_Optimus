"""Portable repo snapshot generator for HUB_Optimus."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MD_OUTPUT = Path("docs/context/TRACEABILITY_SNAPSHOT.md")
DEFAULT_JSON_OUTPUT = Path("docs/context/TRACEABILITY_SNAPSHOT.json")
RECENT_COMMIT_LIMIT = 20


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def detect_repo_root(cwd: Path) -> Path:
    try:
        result = run_git(["rev-parse", "--show-toplevel"], cwd)
    except FileNotFoundError as exc:
        raise RuntimeError("git executable not found") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        message = "not inside a git repository"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message)

    root = result.stdout.strip().splitlines()[0].strip()
    return Path(root).resolve()


def git_text(
    repo_root: Path,
    args: list[str],
    empty_fallback: str,
) -> str:
    result = run_git(args, repo_root)
    text = result.stdout.strip()
    if result.returncode != 0:
        error_text = (result.stderr or text).strip()
        return f"ERROR: {error_text or 'git command failed'}"
    if not text:
        return empty_fallback
    return text


def git_lines(
    repo_root: Path,
    args: list[str],
    empty_fallback: str,
) -> list[str]:
    return git_text(repo_root, args, empty_fallback).splitlines()


def collect_workflows(repo_root: Path) -> list[dict[str, str]]:
    workflows_dir = repo_root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []

    files = sorted(
        path for path in workflows_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".yml", ".yaml"}
    )
    workflows: list[dict[str, str]] = []
    for path in files:
        workflows.append(
            {
                "name": path.name,
                "path": str(path.relative_to(repo_root)).replace("\\", "/"),
                "content": path.read_text(encoding="utf-8", errors="replace").rstrip(),
            }
        )
    return workflows


def collect_inventory(repo_root: Path) -> list[dict[str, str]]:
    inventory: list[dict[str, str]] = []
    for path in sorted(repo_root.iterdir(), key=lambda item: item.name.lower()):
        if path.name == ".git":
            continue
        kind = "dir" if path.is_dir() else "file"
        name = f"{path.name}/" if path.is_dir() else path.name
        inventory.append({"kind": kind, "name": name})
    return inventory


def collect_snapshot(repo_root: Path) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    branch = git_text(repo_root, ["branch", "--show-current"], "(detached HEAD)")
    if branch == "(detached HEAD)":
        branch = git_text(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"], "(detached HEAD)")

    return {
        "timestamp_utc": timestamp,
        "repo_root": str(repo_root),
        "current_branch": branch,
        "head": git_text(repo_root, ["rev-parse", "HEAD"], "UNKNOWN"),
        "remotes": git_lines(repo_root, ["remote", "-v"], "(no remotes configured)"),
        "recent_commits": git_lines(
            repo_root,
            ["log", "--oneline", "--decorate", "-n", str(RECENT_COMMIT_LIMIT)],
            "(no commits found)",
        ),
        "git_status": git_text(repo_root, ["status", "-sb"], "(no status output)"),
        "diff_stats": {
            "unstaged": git_text(repo_root, ["diff", "--stat"], "(no unstaged changes)"),
            "staged": git_text(repo_root, ["diff", "--staged", "--stat"], "(no staged changes)"),
        },
        "workflows": collect_workflows(repo_root),
        "top_level_inventory": collect_inventory(repo_root),
    }


def render_markdown(snapshot: dict[str, Any]) -> str:
    lines: list[str] = [
        "# TRACEABILITY SNAPSHOT",
        "",
        f"- Timestamp: **{snapshot['timestamp_utc']}**",
        f"- Repo root: {snapshot['repo_root']}",
        f"- Branch: **{snapshot['current_branch']}**",
        f"- HEAD: {snapshot['head']}",
        "",
        "## Git status",
        "~~~text",
        snapshot["git_status"],
        "~~~",
        "",
        "## Diff stats (unstaged)",
        "~~~text",
        snapshot["diff_stats"]["unstaged"],
        "~~~",
        "",
        "## Diff stats (staged)",
        "~~~text",
        snapshot["diff_stats"]["staged"],
        "~~~",
        "",
        f"## Recent commits (last {RECENT_COMMIT_LIMIT})",
        "~~~text",
        "\n".join(snapshot["recent_commits"]),
        "~~~",
        "",
        "## Remotes",
        "~~~text",
        "\n".join(snapshot["remotes"]),
        "~~~",
        "",
        "## Top-level inventory",
    ]

    for item in snapshot["top_level_inventory"]:
        lines.append(f"- {item['kind']} {item['name']}")

    lines.extend(["", "## .github/workflows"])

    workflows = snapshot["workflows"]
    if not workflows:
        lines.append("(no workflow files found)")
    else:
        for workflow in workflows:
            lines.extend(
                [
                    "",
                    f"### {workflow['name']}",
                    "~~~yaml",
                    workflow["content"],
                    "~~~",
                ]
            )

    return "\n".join(lines) + "\n"


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-md",
        type=Path,
        default=None,
        help="Write the markdown snapshot to PATH.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Write the JSON snapshot to PATH.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    try:
        repo_root = detect_repo_root(Path.cwd())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    snapshot = collect_snapshot(repo_root)
    markdown = render_markdown(snapshot)

    md_path = args.output_md or (repo_root / DEFAULT_MD_OUTPUT)
    json_path = args.output_json or (repo_root / DEFAULT_JSON_OUTPUT)

    write_text_file(md_path, markdown)
    write_json_file(json_path, snapshot)

    print(f"OK: wrote {md_path}")
    print(f"OK: wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
