from __future__ import annotations

import argparse
import subprocess
import sys

# Keep this list aligned with docs/context/STATUS.md.
# v1 core canonical specs are in es/, en/ is parity reference.
PROTECTED_PREFIXES = (
    "v1_core/languages/es/",
    "v1_core/languages/en/",
    "docs/governance/",
    "KERNEL_CHARTER.md",
    "KERNEL_CHARTER_EN.md",
)


def _normalize(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _is_protected(path: str) -> bool:
    normalized = _normalize(path)
    return any(normalized.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def _changed_files(base_ref: str | None, head_ref: str | None, staged: bool) -> list[str]:
    cmd = ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]

    if staged:
        cmd.append("--cached")
    elif base_ref and head_ref:
        cmd.append(f"{base_ref}...{head_ref}")
    elif base_ref:
        cmd.append(base_ref)
    else:
        cmd.append("HEAD")

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git diff failed")

    return [_normalize(line) for line in proc.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail when protected kernel paths are changed without explicit override."
    )
    parser.add_argument("--base-ref", default=None, help="Base git ref for diff (e.g. origin/main)")
    parser.add_argument("--head-ref", default=None, help="Head git ref for diff (default: current HEAD)")
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Inspect staged changes instead of ref-based diff",
    )
    parser.add_argument(
        "--allow-kernel-changes",
        action="store_true",
        help="Allow protected path changes for intentional kernel/governance updates",
    )
    args = parser.parse_args()

    try:
        changed = _changed_files(args.base_ref, args.head_ref, args.staged)
    except RuntimeError as exc:
        print(f"[kernel-guard] error: {exc}", file=sys.stderr)
        return 2

    protected = [path for path in changed if _is_protected(path)]
    if not protected:
        print("[kernel-guard] OK: no protected kernel/governance paths changed.")
        return 0

    if args.allow_kernel_changes:
        print("[kernel-guard] bypass enabled: protected paths changed intentionally:")
        for path in protected:
            print(f"- {path}")
        return 0

    print("[kernel-guard] blocked: protected paths changed:", file=sys.stderr)
    for path in protected:
        print(f"- {path}", file=sys.stderr)
    print(
        "Re-run with --allow-kernel-changes for intentional edits and include impact notes in PR.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
