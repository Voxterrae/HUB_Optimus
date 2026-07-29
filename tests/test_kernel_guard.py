from __future__ import annotations

import subprocess
from pathlib import Path

from tools.kernel_guard import (
    DEFAULT_PROTECTED_PREFIXES,
    changed_files,
    protected_changes,
)


def run_git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def initialize_repository(repository: Path, files: dict[str, str]) -> str:
    run_git(repository, "init", "-q")
    run_git(repository, "config", "user.name", "Kernel Guard Test")
    run_git(repository, "config", "user.email", "kernel-guard@example.invalid")

    for relative_path, content in files.items():
        path = repository / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    run_git(repository, "add", ".")
    run_git(repository, "commit", "-qm", "base")
    return run_git(repository, "rev-parse", "HEAD")


def commit_all(repository: Path, message: str) -> str:
    run_git(repository, "add", "-A")
    run_git(repository, "commit", "-qm", message)
    return run_git(repository, "rev-parse", "HEAD")


def assert_protected_change(
    repository: Path,
    monkeypatch,
    base_sha: str,
    head_sha: str,
    expected_path: str,
) -> None:
    monkeypatch.chdir(repository)
    paths = changed_files(base_sha, head_sha)
    assert expected_path in paths
    assert expected_path in protected_changes(paths, DEFAULT_PROTECTED_PREFIXES)


def test_protected_file_addition_is_detected(tmp_path: Path, monkeypatch):
    base_sha = initialize_repository(tmp_path, {"README.md": "base\n"})
    protected = tmp_path / "docs" / "governance" / "NEW_POLICY.md"
    protected.parent.mkdir(parents=True)
    protected.write_text("new policy\n", encoding="utf-8")
    head_sha = commit_all(tmp_path, "add protected file")

    assert_protected_change(
        tmp_path,
        monkeypatch,
        base_sha,
        head_sha,
        "docs/governance/NEW_POLICY.md",
    )


def test_protected_file_deletion_is_detected(tmp_path: Path, monkeypatch):
    relative_path = "docs/governance/POLICY.md"
    base_sha = initialize_repository(tmp_path, {relative_path: "policy\n"})
    (tmp_path / relative_path).unlink()
    head_sha = commit_all(tmp_path, "delete protected file")

    assert_protected_change(
        tmp_path,
        monkeypatch,
        base_sha,
        head_sha,
        relative_path,
    )


def test_rename_out_of_protected_zone_is_detected(tmp_path: Path, monkeypatch):
    relative_path = "docs/governance/POLICY.md"
    base_sha = initialize_repository(tmp_path, {relative_path: "policy\n"})
    destination = tmp_path / "docs" / "notes" / "POLICY.md"
    destination.parent.mkdir(parents=True)
    (tmp_path / relative_path).rename(destination)
    head_sha = commit_all(tmp_path, "move protected file")

    assert_protected_change(
        tmp_path,
        monkeypatch,
        base_sha,
        head_sha,
        relative_path,
    )


def test_protected_file_modification_is_detected(tmp_path: Path, monkeypatch):
    relative_path = "v1_core/languages/es/README.md"
    base_sha = initialize_repository(tmp_path, {relative_path: "canonical\n"})
    (tmp_path / relative_path).write_text("changed\n", encoding="utf-8")
    head_sha = commit_all(tmp_path, "modify protected file")

    assert_protected_change(
        tmp_path,
        monkeypatch,
        base_sha,
        head_sha,
        relative_path,
    )


def test_guard_file_is_itself_protected(tmp_path: Path, monkeypatch):
    relative_path = "tools/kernel_guard.py"
    base_sha = initialize_repository(tmp_path, {relative_path: "print('base')\n"})
    (tmp_path / relative_path).write_text("print('changed')\n", encoding="utf-8")
    head_sha = commit_all(tmp_path, "modify guard")

    assert_protected_change(
        tmp_path,
        monkeypatch,
        base_sha,
        head_sha,
        relative_path,
    )
