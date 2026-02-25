#!/usr/bin/env python3
from __future__ import annotations

import argparse
from fnmatch import fnmatch
import re
import sys
from pathlib import Path


DEFAULT_TARGETS = (".",)
EXCLUDED_DIR_NAMES = {".git", ".venv", "site", "node_modules"}
EXCLUDED_DIR_PATTERNS = ("out_*",)

PATTERNS = (
    ("replacement_char", re.compile(r"\uFFFD")),
    ("double_utf8_A_tilde", re.compile(r"Ã[\w\u0080-\u00FF]")),
    ("double_utf8_A_circumflex", re.compile(r"Â[\w\u0080-\u00FF]")),
    ("smart_punct_mojibake", re.compile(r"â[€™“”–—€¦¢„™]")),
    ("double_encoded_cyrillic", re.compile(r"Гўв‚¬|вЂ™|вЂњ|вЂќ|вЂ”|вЂ“")),
)


def iter_markdown_files(target: Path) -> list[Path]:
    def is_excluded(path: Path) -> bool:
        return any(
            part in EXCLUDED_DIR_NAMES
            or any(fnmatch(part, pattern) for pattern in EXCLUDED_DIR_PATTERNS)
            for part in path.parts
        )

    if target.is_file():
        resolved = target.resolve()
        return [resolved] if resolved.suffix.lower() == ".md" and not is_excluded(resolved) else []
    if not target.exists():
        return []
    return sorted(
        p.resolve()
        for p in target.rglob("*.md")
        if p.is_file() and not is_excluded(p.resolve())
    )


def scan_file(path: Path, root: Path) -> list[str]:
    rel = path.resolve().relative_to(root.resolve())
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"{rel}:1: utf-8 decode error: {exc}"]

    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(f"{rel}:{lineno}: [{name}] {line.strip()}")
                break
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect common mojibake signatures in markdown files."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help=(
            "Files or directories to scan (default: repo root). "
            "Excludes .git, .venv, site, node_modules, and out_* directories."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path.cwd()
    targets = [Path(t) for t in (args.targets or DEFAULT_TARGETS)]

    files: list[Path] = []
    for target in targets:
        files.extend(iter_markdown_files(target))
    files = sorted(set(files))

    findings: list[str] = []
    for path in files:
        findings.extend(scan_file(path, root))

    if findings:
        print("Mojibake signatures detected:", file=sys.stderr)
        for finding in findings:
            print(f" - {finding}", file=sys.stderr)
        return 1

    print(f"Mojibake check passed ({len(files)} markdown files scanned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
