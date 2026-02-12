#!/usr/bin/env python3
import sys
import subprocess

ALLOW = (sys.argv[1].strip().lower() == "true") if len(sys.argv) > 1 else False

PROTECTED_PREFIXES = (
    "docs/governance/",
    "v1_core/languages/en/",
)


def changed_files():
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    files = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        files.append(line[3:])
    return files


def main():
    files = changed_files()
    protected = [path for path in files if path.startswith(PROTECTED_PREFIXES)]

    if protected and not ALLOW:
        print(
            "KERNEL GUARD BLOCKED: protected files changed but allow_kernel_changes=false"
        )
        for path in protected:
            print(" -", path)
        sys.exit(1)

    print("Kernel guard OK. Protected changed:", protected)


if __name__ == "__main__":
    main()
