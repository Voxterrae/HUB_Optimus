#!/usr/bin/env python3
import os
import subprocess
import sys


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ensure_label(name, color="0E8A16", description=""):
    code, out, _ = run(
        [
            "gh",
            "label",
            "list",
            "--json",
            "name",
            "--jq",
            f'.[] | select(.name=="{name}") | .name',
        ]
    )
    if code == 0 and out == name:
        return
    run(["gh", "label", "create", name, "--color", color, "--description", description])


def get_changed_files():
    code, out, _ = run(["git", "diff", "--name-only", "origin/main...HEAD"])
    if code != 0:
        code, out, _ = run(["git", "diff", "--name-only"])
        if code != 0:
            return []
    return [line for line in out.splitlines() if line.strip()]


def main():
    pr_number = os.environ.get("PR_NUMBER", "").strip()
    mode = os.environ.get("MODE", "full")
    allow_kernel = os.environ.get("ALLOW_KERNEL", "false")

    ensure_label("maintenance", "0E8A16", "Automated maintenance PR")
    ensure_label(
        "kernel-change",
        "B60205",
        "Touches Kernel/Governance protected files",
    )
    ensure_label("i18n", "1D76DB", "Language mirror / translation structure updates")

    files = get_changed_files()

    labels = ["maintenance"]
    if mode in ("i18n", "full"):
        labels.append("i18n")
    if any(
        path.startswith("docs/governance/") or path.startswith("v1_core/languages/en/")
        for path in files
    ):
        labels.append("kernel-change")

    body_lines = [
        "### Automated maintenance summary",
        f"- Mode: `{mode}`",
        f"- allow_kernel_changes: `{allow_kernel}`",
        "",
        "#### Changed files",
    ]
    for path in files[:200]:
        body_lines.append(f"- `{path}`")
    if len(files) > 200:
        body_lines.append(f"- ...and {len(files) - 200} more")

    comment = "\n".join(body_lines)

    if pr_number:
        run(["gh", "pr", "edit", pr_number, "--add-label"] + labels)
        run(["gh", "pr", "comment", pr_number, "--body", comment])
    else:
        branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("BRANCH_NAME")
        if not branch:
            print("No PR_NUMBER or branch ref available.")
            sys.exit(0)

    print("pr_pro done")


if __name__ == "__main__":
    main()
