#!/usr/bin/python3 -I
"""Supported EC2 operator entrypoint with no ambient Bash boundary."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path


APP_ROOT = Path("/opt/hub-optimus")
SYSTEM_PYTHON = "/usr/bin/python3"
GIT = "/usr/bin/git"
SCRIPT_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_REPOSITORY = "https://github.com/Voxterrae/HUB_Optimus.git"
MUTATING_OPERATIONS = frozenset({"adopt", "deploy", "preflight", "rollback"})


def usage(stream=sys.stdout) -> None:
    print(
        """HUB_Optimus EC2 ops

Usage:
  hub-ops status
  hub-ops validate
  hub-ops preflight <full-commit-sha> <https-reference-url>
  hub-ops adopt <full-current-commit-sha>
  hub-ops deploy <commit-sha-or-tag>
  hub-ops rollback

Commands:
  status    Show current release, previous release, state, commit, source changes, releases and disk usage.
  validate  Validate the current release through the isolated pytest supervisor.
  preflight Run the reviewed read-only host preflight through a clean boundary.
  adopt     Adopt one exact legacy current commit through a clean boundary.
  deploy    Deploy one explicit reviewed full commit SHA or tag.
  rollback  Run rollback-current through a clean boundary.
""",
        file=stream,
        end="",
    )


def fail(message: str) -> None:
    print(f"[hub-ops:error] {message}", file=sys.stderr)
    raise SystemExit(1)


def clean_environment() -> dict[str, str]:
    # Construct from nothing: neither Bash startup hooks/exported functions nor
    # Python, pytest, Git, or pip caller configuration crosses this boundary.
    return {
        "HOME": "/nonexistent",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
    }


def read_or_none(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").rstrip("\n") or "none"
    except (OSError, UnicodeError):
        return "none"


def current_release() -> Path | None:
    current = APP_ROOT / "current"
    if not current.is_symlink():
        return None
    try:
        resolved = Path(os.path.realpath(current))
        info = resolved.stat(follow_symlinks=False)
    except OSError:
        return None
    return resolved if stat.S_ISDIR(info.st_mode) else None


def git(release: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [GIT, "-C", str(release), *arguments],
        cwd="/",
        env=clean_environment(),
        capture_output=True,
        text=True,
        check=False,
    )


def show_section(label: str, value: str) -> None:
    print(f"[status] {label}:")
    print(value or "none")
    print()


def status_current() -> None:
    print("[status] HUB_Optimus EC2\n")
    release = current_release()
    show_section("current", str(release) if release is not None else "none")
    show_section("previous", read_or_none(APP_ROOT / "shared" / "previous_release"))
    show_section("current_release", read_or_none(APP_ROOT / "shared" / "current_release"))
    show_section("release_state", read_or_none(APP_ROOT / "shared" / "RELEASE_STATE"))
    show_section("last_rollback_from", read_or_none(APP_ROOT / "shared" / "last_rollback_from"))

    if release is None:
        show_section("git commit", "none")
        show_section("git status", "none")
    else:
        commit = git(release, "rev-parse", "--verify", "HEAD^{commit}")
        commit_value = commit.stdout.strip()
        show_section(
            "git commit",
            commit_value if commit.returncode == 0 else "unavailable",
        )
        show_section(
            "source status",
            "not evaluated by read-only status; run hub-ops validate",
        )

    releases = APP_ROOT / "releases"
    try:
        names = sorted(item.name for item in releases.iterdir())
    except OSError:
        names = []
    show_section("releases", "\n".join(names) if names else "none")
    try:
        disk = os.statvfs(APP_ROOT)
        available = disk.f_bavail * disk.f_frsize
        total = disk.f_blocks * disk.f_frsize
        disk_value = f"available_bytes={available} total_bytes={total}"
    except OSError:
        disk_value = "unavailable"
    show_section("disk", disk_value)


def operation_tools(release: Path | None = None) -> Path:
    # A retained reviewed checkout keeps the complete toolset adjacent. An
    # installed standalone hub-ops falls back to the active reviewed release.
    if (SCRIPT_DIRECTORY / "run-reviewed-operation.py").is_file():
        return SCRIPT_DIRECTORY
    if release is None:
        release = current_release()
    if release is None:
        fail("no reviewed operation toolset is available")
    return release / "ops" / "ec2"


def validate_tool(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        fail(f"cannot inspect {label}: {exc}")
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        fail(f"{label} is not one regular file: {path}")
    if info.st_uid != os.geteuid() or info.st_nlink != 1:
        fail(f"{label} has unsafe identity: {path}")
    if stat.S_IMODE(info.st_mode) & 0o022:
        fail(f"{label} is group- or world-writable: {path}")


def validate_current() -> None:
    release = current_release()
    if release is None:
        fail("current symlink does not identify one release directory")
    resolved = git(release, "rev-parse", "--verify", "HEAD^{commit}")
    commit = resolved.stdout.strip()
    if resolved.returncode != 0 or len(commit) != 40 or any(
        character not in "0123456789abcdef" for character in commit
    ):
        fail("current release does not resolve to one full commit SHA")
    tools = operation_tools(release)
    runner = tools / "run-release-validation.py"
    verifier = tools / "verify-release-worktree.py"
    validate_tool(runner, "validation supervisor")
    validate_tool(verifier, "source-tree verifier")
    command = [
        SYSTEM_PYTHON,
        "-I",
        str(runner),
        str(release),
        commit,
        str(verifier),
    ]
    os.execve(command[0], command, clean_environment())


def run_operation(operation: str, arguments: list[str]) -> None:
    tools = operation_tools()
    dispatcher = tools / "run-reviewed-operation.py"
    validate_tool(dispatcher, "reviewed-operation dispatcher")
    command = [
        SYSTEM_PYTHON,
        "-I",
        str(dispatcher),
        "--app-root",
        str(APP_ROOT),
        "--repo-url",
        DEFAULT_REPOSITORY,
        operation,
        *arguments,
    ]
    os.execve(command[0], command, clean_environment())


def main() -> None:
    arguments = sys.argv[1:]
    if not arguments or arguments[0] in {"-h", "--help", "help"}:
        if len(arguments) > 1:
            fail("help accepts no arguments")
        usage()
        return
    command, *remaining = arguments
    if command == "status":
        if remaining:
            fail("status accepts no arguments")
        status_current()
        return
    if command == "validate":
        if remaining:
            fail("validate accepts no arguments")
        validate_current()
        return
    if command in MUTATING_OPERATIONS:
        run_operation(command, remaining)
        return
    usage(sys.stderr)
    fail(f"unknown command: {command}")


if __name__ == "__main__":
    main()
