#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Iterable


DEFAULT_PROTECTED_PREFIXES = (
    "docs/governance/",
    "v1_core/languages/es/",
)


def _run_git(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{stderr}")
    return proc.stdout


def changed_files(base_ref: str | None, head_ref: str) -> list[str]:
    if base_ref:
        output = _run_git(
            [
                "git",
                "diff",
                "--name-only",
                "--diff-filter=ACMR",
                f"{base_ref}..{head_ref}",
            ]
        )
        return [line.strip() for line in output.splitlines() if line.strip()]

    # Backward-compatible local mode: inspect working tree changes.
    output = _run_git(["git", "status", "--porcelain"])
    files: list[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        files.append(line[3:].strip())
    return files


def protected_changes(paths: Iterable[str], prefixes: tuple[str, ...]) -> list[str]:
    return sorted(path for path in paths if path.startswith(prefixes))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Block changes in protected kernel/governance paths unless override is enabled."
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help="Base git ref for diff mode (example: origin/main).",
    )
    parser.add_argument(
        "--head-ref",
        default="HEAD",
        help="Head git ref for diff mode. Defaults to HEAD.",
    )
    parser.add_argument(
        "--allow-kernel-changes",
        action="store_true",
        help="Allow protected-path changes (use only with auditable governance override).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        files = changed_files(args.base_ref, args.head_ref)
    except RuntimeError as exc:
        print(f"Kernel guard failed to compute changed files: {exc}", file=sys.stderr)
        return 2

    blocked = protected_changes(files, DEFAULT_PROTECTED_PREFIXES)

    if blocked and not args.allow_kernel_changes:
        print(
            "KERNEL GUARD BLOCKED: protected files changed and override is not enabled.",
            file=sys.stderr,
        )
        print(
            "To override in PR workflow, apply auditable label 'allow-kernel-change'.",
            file=sys.stderr,
        )
        print("Blocked files:", file=sys.stderr)
        for path in blocked:
            print(f" - {path}", file=sys.stderr)
        return 1

    if blocked and args.allow_kernel_changes:
        print("Kernel guard override active. Protected changes allowed:")
        for path in blocked:
            print(f" - {path}")
        return 0

    print("Kernel guard OK: no protected path changes detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
