#!/usr/bin/env python3
"""Detect maintenance drift without modifying the repository checkout.

The legacy maintenance helper is executed only inside an isolated copy of the
committed Git tree. The candidate copy is compared with an untouched baseline.

Exit codes:
    0: no drift
    1: drift detected
    2: check could not complete safely
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


REPO = Path(__file__).resolve().parents[1]
MAX_SUMMARY_PATHS = 100


@dataclass(frozen=True)
class FileState:
    kind: str
    mode: int
    digest: str


@dataclass(frozen=True)
class Drift:
    change: str
    path: str


def run_git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def clean_status() -> str:
    return run_git("status", "--porcelain=v1", "--untracked-files=all")


def safe_extract(archive: bytes, destination: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        for member in bundle.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(f"unsafe path in Git archive: {member.name!r}")
        bundle.extractall(destination, filter="data")


def snapshot(root: Path) -> dict[str, FileState]:
    inventory: dict[str, FileState] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            target = os.readlink(path)
            digest = hashlib.sha256(target.encode("utf-8")).hexdigest()
            inventory[relative] = FileState("symlink", mode, digest)
        elif path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            inventory[relative] = FileState("file", mode, digest)
    return inventory


def compare(
    baseline: dict[str, FileState],
    candidate: dict[str, FileState],
) -> list[Drift]:
    changes: list[Drift] = []
    for path in sorted(baseline.keys() | candidate.keys()):
        if path not in baseline:
            changes.append(Drift("A", path))
        elif path not in candidate:
            changes.append(Drift("D", path))
        elif baseline[path] != candidate[path]:
            changes.append(Drift("M", path))
    return changes


def markdown_path(path: str) -> str:
    escaped = path.replace("`", "ˋ").replace("|", "\\|")
    return f"`{escaped}`"


def render_summary(
    *,
    commit: str,
    mode: str,
    status: str,
    detail: str,
    changes: list[Drift] | None = None,
    bot_output: str = "",
) -> str:
    lines = [
        "## Repository maintenance drift",
        "",
        f"- Commit: `{commit}`",
        f"- Mode: `{mode}`",
        f"- Status: **{status}**",
        f"- Detail: {detail}",
    ]
    if changes:
        lines.extend(
            [
                "",
                "| Change | Path |",
                "|---|---|",
            ]
        )
        for drift in changes[:MAX_SUMMARY_PATHS]:
            lines.append(f"| `{drift.change}` | {markdown_path(drift.path)} |")
        remaining = len(changes) - MAX_SUMMARY_PATHS
        if remaining > 0:
            lines.extend(["", f"{remaining} additional changed paths omitted."])
    if bot_output.strip():
        output = bot_output.strip()
        if len(output) > 4_000:
            output = f"{output[:4_000]}\n… output truncated"
        lines.extend(["", "<details>", "<summary>Maintenance helper output</summary>", "", "```text"])
        lines.extend(output.splitlines())
        lines.extend(["```", "</details>"])
    return "\n".join(lines) + "\n"


def publish_summary(summary: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(summary)
    print(summary, end="")


def run_check(mode: str) -> tuple[int, str]:
    commit = run_git("rev-parse", "HEAD")
    initial_status = clean_status()
    if initial_status:
        return 2, render_summary(
            commit=commit,
            mode=mode,
            status="error",
            detail="The source checkout is not clean; the check stopped fail-closed.",
        )

    archive_result = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=REPO,
        check=True,
        capture_output=True,
    )

    with tempfile.TemporaryDirectory(prefix="hub-optimus-maintenance-") as temporary:
        temporary_root = Path(temporary)
        baseline_root = temporary_root / "baseline"
        candidate_root = temporary_root / "candidate"
        baseline_root.mkdir()
        safe_extract(archive_result.stdout, baseline_root)
        shutil.copytree(baseline_root, candidate_root, symlinks=True)

        helper = candidate_root / "tools" / "maintenance_bot.py"
        if not helper.is_file():
            return 2, render_summary(
                commit=commit,
                mode=mode,
                status="error",
                detail="The committed maintenance helper is missing.",
            )

        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run(
            [sys.executable, str(helper), mode],
            cwd=candidate_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=120,
        )
        bot_output = "\n".join(
            part for part in (result.stdout.strip(), result.stderr.strip()) if part
        )
        if result.returncode != 0:
            return 2, render_summary(
                commit=commit,
                mode=mode,
                status="error",
                detail=(
                    "The maintenance helper exited "
                    f"{result.returncode}; the check stopped fail-closed."
                ),
                bot_output=bot_output,
            )

        changes = compare(snapshot(baseline_root), snapshot(candidate_root))

    final_status = clean_status()
    if final_status != initial_status:
        return 2, render_summary(
            commit=commit,
            mode=mode,
            status="error",
            detail="The source checkout changed during the check.",
        )

    if changes:
        return 1, render_summary(
            commit=commit,
            mode=mode,
            status="drift detected",
            detail=(
                f"The isolated maintenance run proposed {len(changes)} changed "
                "path(s). No repository files, commits, or refs were modified."
            ),
            changes=changes,
            bot_output=bot_output,
        )

    return 0, render_summary(
        commit=commit,
        mode=mode,
        status="clean",
        detail=(
            "The isolated maintenance run matched the committed tree. "
            "No repository files, commits, or refs were modified."
        ),
        bot_output=bot_output,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repository maintenance in isolation and report drift."
    )
    parser.add_argument(
        "--mode",
        default="full",
        help="Mode passed to tools/maintenance_bot.py (default: full).",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    try:
        exit_code, summary = run_check(arguments.mode)
    except (OSError, RuntimeError, subprocess.SubprocessError, tarfile.TarError) as error:
        try:
            commit = run_git("rev-parse", "HEAD")
        except (OSError, subprocess.SubprocessError):
            commit = "unavailable"
        exit_code = 2
        summary = render_summary(
            commit=commit,
            mode=arguments.mode,
            status="error",
            detail=f"The drift check could not complete safely: {error}",
        )

    try:
        publish_summary(summary)
    except OSError as error:
        print(f"Failed to publish maintenance summary: {error}", file=sys.stderr)
        return 2
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
