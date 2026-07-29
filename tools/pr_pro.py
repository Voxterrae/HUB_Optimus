#!/usr/bin/env python3
"""Fail-closed label and summary enrichment for an existing GitHub PR.

Support status: supported as a small, optional repository utility.  It is not
a PR creator, merge authority, or authentication provider.  Write mode uses
the caller's existing ``gh`` authentication and scopes.  ``--dry-run`` runs
the local diff only and never invokes ``gh``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence


ERROR_EXIT_CODE = 2


class PrProError(RuntimeError):
    """A concise, expected failure that must stop PR enrichment."""


def _concise_detail(*values: str, limit: int = 240) -> str:
    detail = " ".join(" ".join(value.split()) for value in values if value.strip())
    if not detail:
        return "no diagnostic output"
    return detail if len(detail) <= limit else f"{detail[: limit - 3]}..."


def run_command(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run one external command without a shell and preserve its result."""
    try:
        return subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise PrProError(f"cannot execute {cmd[0]}: {exc}") from exc


def _require_success(
    result: subprocess.CompletedProcess[str],
    operation: str,
) -> str:
    if result.returncode != 0:
        detail = _concise_detail(result.stderr, result.stdout)
        raise PrProError(f"{operation} failed ({result.returncode}): {detail}")
    return result.stdout.strip()


def ensure_label(
    name: str,
    color: str = "0E8A16",
    description: str = "",
    *,
    dry_run: bool = False,
) -> None:
    """Ensure one label exists, or report the mutation in dry-run mode."""
    if dry_run:
        print(f"[dry-run] ensure label: {name}")
        return

    listed = run_command(
        [
            "gh",
            "label",
            "list",
            "--limit",
            "1000",
            "--json",
            "name",
            "--jq",
            f'.[] | select(.name=="{name}") | .name',
        ]
    )
    output = _require_success(listed, f"list label {name!r}")
    if name in output.splitlines():
        return

    created = run_command(
        [
            "gh",
            "label",
            "create",
            name,
            "--color",
            color,
            "--description",
            description,
        ]
    )
    _require_success(created, f"create label {name!r}")


def get_changed_files() -> list[str]:
    """Return branch changes against main, without a weaker local fallback."""
    against_main = run_command(
        ["git", "diff", "--name-only", "origin/main...HEAD"]
    )
    output = _require_success(
        against_main,
        "read changed files against origin/main",
    )
    return [line for line in output.splitlines() if line.strip()]


def _validated_pr_number(value: str) -> str:
    if not value.isdigit() or int(value) < 1:
        raise PrProError(f"invalid PR_NUMBER: {value!r}")
    return value


def resolve_pr_target(
    pr_number: str,
    branch: str,
    *,
    dry_run: bool,
) -> tuple[str | None, str]:
    """Resolve an existing PR number, without using GitHub in dry-run mode."""
    if pr_number:
        validated = _validated_pr_number(pr_number)
        if dry_run:
            return None, f"PR #{validated}"
        selector = validated
        operation = f"validate PR #{validated}"
    else:
        if not branch:
            raise PrProError("PR_NUMBER or GITHUB_HEAD_REF/BRANCH_NAME is required")
        if dry_run:
            return None, f"PR for branch {branch!r}"
        selector = branch
        operation = f"resolve PR for branch {branch!r}"

    viewed = run_command(
        ["gh", "pr", "view", selector, "--json", "number", "--jq", ".number"]
    )
    resolved = _require_success(viewed, operation)
    return _validated_pr_number(resolved), f"PR #{resolved}"


def _build_comment(files: list[str], mode: str, allow_kernel: str) -> str:
    body_lines = [
        "### Automated maintenance summary",
        f"- Mode: `{mode}`",
        f"- allow_kernel_changes: `{allow_kernel}`",
        "",
        "#### Changed files",
    ]
    body_lines.extend(f"- `{path}`" for path in files[:200])
    if len(files) > 200:
        body_lines.append(f"- ...and {len(files) - 200} more")
    return "\n".join(body_lines)


def _labels_for(files: list[str], mode: str) -> list[str]:
    labels = ["maintenance"]
    if mode in ("i18n", "full"):
        labels.append("i18n")
    if any(
        path.startswith("docs/governance/")
        or path.startswith("v1_core/languages/en/")
        for path in files
    ):
        labels.append("kernel-change")
    return labels


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add governed labels and a changed-file summary to an existing PR."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned PR enrichment without invoking any gh command.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    pr_number = os.environ.get("PR_NUMBER", "").strip()
    branch = (
        os.environ.get("GITHUB_HEAD_REF")
        or os.environ.get("BRANCH_NAME")
        or ""
    ).strip()
    mode = os.environ.get("MODE", "full")
    allow_kernel = os.environ.get("ALLOW_KERNEL", "false")

    try:
        if not args.dry_run and shutil.which("gh") is None:
            raise PrProError("GitHub CLI 'gh' is required for write mode")

        resolved_pr, target_description = resolve_pr_target(
            pr_number,
            branch,
            dry_run=args.dry_run,
        )
        files = get_changed_files()
        labels = _labels_for(files, mode)
        comment = _build_comment(files, mode, allow_kernel)

        label_specs = (
            ("maintenance", "0E8A16", "Automated maintenance PR"),
            ("kernel-change", "B60205", "Touches Kernel/Governance protected files"),
            ("i18n", "1D76DB", "Language mirror / translation structure updates"),
        )
        for name, color, description in label_specs:
            ensure_label(
                name,
                color,
                description,
                dry_run=args.dry_run,
            )

        if args.dry_run:
            print(f"[dry-run] target: {target_description}")
            print(f"[dry-run] add labels: {', '.join(labels)}")
            print("[dry-run] post comment:")
            print(comment)
            print("pr_pro dry-run complete; no GitHub commands executed")
            return 0

        if resolved_pr is None:  # Defensive: normal mode always resolves a number.
            raise PrProError("internal error: PR target was not resolved")

        edited = run_command(
            [
                "gh",
                "pr",
                "edit",
                resolved_pr,
                "--add-label",
                ",".join(labels),
            ]
        )
        _require_success(edited, f"add labels to PR #{resolved_pr}")

        commented = run_command(
            ["gh", "pr", "comment", resolved_pr, "--body", comment]
        )
        _require_success(commented, f"comment on PR #{resolved_pr}")
    except PrProError as exc:
        print(f"[pr-pro-error] {exc}", file=sys.stderr)
        return ERROR_EXIT_CODE

    print("pr_pro done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
