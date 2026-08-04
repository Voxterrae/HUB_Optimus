#!/usr/bin/env python3
"""Launch reviewed EC2 operations across a non-Bash environment boundary."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path


DEFAULT_APP_ROOT = "/opt/hub-optimus"
DEFAULT_REPOSITORY = "https://github.com/Voxterrae/HUB_Optimus.git"
OPERATIONS = {
    "adopt": ("adopt-legacy-current.sh", 1),
    "deploy": ("deploy-current.sh", 1),
    "preflight": ("preflight-deploy.sh", 2),
    "rollback": ("rollback-current.sh", 0),
}


def fail(message: str) -> None:
    print(f"[reviewed-operation:error] {message}", file=sys.stderr)
    raise SystemExit(1)


def canonical_absolute(raw: str, label: str) -> str:
    if not os.path.isabs(raw) or os.path.abspath(raw) != raw:
        fail(f"{label} must be one canonical absolute path")
    return raw


def validate_script(path: Path) -> None:
    try:
        visible = path.lstat()
    except OSError as exc:
        fail(f"cannot inspect reviewed operation script {path}: {exc}")
    if not stat.S_ISREG(visible.st_mode) or path.is_symlink():
        fail(f"reviewed operation script is not one regular file: {path}")
    if visible.st_uid != os.geteuid():
        fail(f"reviewed operation script has an unexpected owner: {path}")
    if visible.st_nlink != 1:
        fail(f"reviewed operation script has more than one link: {path}")
    if stat.S_IMODE(visible.st_mode) & 0o022:
        fail(f"reviewed operation script is group- or world-writable: {path}")


def clean_environment(app_root: str, repository: str) -> dict[str, str]:
    # This is intentionally constructed from nothing. In particular, Bash never
    # observes BASH_ENV/exported functions and Python/pytest/git/pip receive no
    # ambient configuration from the caller.
    return {
        "HOME": "/nonexistent",
        "HUB_OPTIMUS_APP_ROOT": app_root,
        "HUB_OPTIMUS_REPO_URL": repository,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one reviewed HUB_Optimus EC2 operation",
    )
    parser.add_argument("--app-root", default=DEFAULT_APP_ROOT)
    parser.add_argument("--repo-url", default=DEFAULT_REPOSITORY)
    parser.add_argument("operation", choices=sorted(OPERATIONS))
    parser.add_argument("operation_arguments", nargs="*")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    app_root = canonical_absolute(arguments.app_root, "APP_ROOT")
    repository = arguments.repo_url
    if not repository.startswith("https://"):
        canonical_absolute(repository, "local repository path")

    script_name, required_arguments = OPERATIONS[arguments.operation]
    if len(arguments.operation_arguments) != required_arguments:
        fail(
            f"{arguments.operation} requires exactly "
            f"{required_arguments} operation argument(s)"
        )

    script_directory = Path(__file__).resolve().parent
    script = script_directory / script_name
    validate_script(script)
    environment = clean_environment(app_root, repository)
    command = [
        "/bin/bash",
        "--noprofile",
        "--norc",
        str(script),
        *arguments.operation_arguments,
    ]
    os.execve(command[0], command, environment)


if __name__ == "__main__":
    main()
