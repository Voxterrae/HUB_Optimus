"""Tests for the portable traceability snapshot CLI."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "trace_repo.py"


def run_tool(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result


def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        "name: CI\non: push\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("# Temp repo\n", encoding="utf-8")

    git(repo, "init")
    git(repo, "checkout", "-b", "main")
    git(repo, "config", "user.email", "trace@example.com")
    git(repo, "config", "user.name", "Trace Tester")
    git(repo, "remote", "add", "origin", "https://example.com/org/repo.git")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "initial commit")
    return repo


def test_trace_repo_writes_markdown_and_json_with_custom_paths(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "README.md").write_text("# Temp repo\nupdated\n", encoding="utf-8")
    (repo / "staged.txt").write_text("staged change\n", encoding="utf-8")
    git(repo, "add", "staged.txt")

    md_path = repo / "out" / "trace.md"
    json_path = repo / "out" / "trace.json"

    result = run_tool("--output-md", str(md_path), "--output-json", str(json_path), cwd=repo)

    assert result.returncode == 0, result.stderr
    assert md_path.is_file()
    assert json_path.is_file()

    markdown = md_path.read_text(encoding="utf-8")
    assert "# TRACEABILITY SNAPSHOT" in markdown
    assert "## Git status" in markdown
    assert "## Diff stats (staged)" in markdown
    assert "## .github/workflows" in markdown
    assert "### ci.yml" in markdown
    assert "staged.txt" in markdown

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["repo_root"] == str(repo.resolve())
    assert payload["current_branch"] == "main"
    assert len(payload["head"]) == 40
    assert any("origin" in line for line in payload["remotes"])
    assert payload["recent_commits"]
    assert "staged.txt" in payload["diff_stats"]["staged"]
    assert "README.md" in payload["diff_stats"]["unstaged"]
    assert payload["workflows"][0]["name"] == "ci.yml"
    assert payload["workflows"][0]["content"] == "name: CI\non: push"
    assert any(item["name"] == ".github/" for item in payload["top_level_inventory"])


def test_trace_repo_uses_default_docs_context_outputs(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    result = run_tool(cwd=repo)

    assert result.returncode == 0, result.stderr
    assert (repo / "docs" / "context" / "TRACEABILITY_SNAPSHOT.md").is_file()
    assert (repo / "docs" / "context" / "TRACEABILITY_SNAPSHOT.json").is_file()


def test_trace_repo_fails_outside_git_repo(tmp_path: Path) -> None:
    result = run_tool(cwd=tmp_path)

    assert result.returncode != 0
    assert "not inside a git repository" in result.stderr.lower()
