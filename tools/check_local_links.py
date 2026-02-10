#!/usr/bin/env python3
"""check_local_links.py

Local (offline) link checker for HUB_Optimus.

Why this exists:
- The repo uses GitHub Actions + lychee for link checking.
- When working locally (or when adding new languages), it's useful to catch
  broken *relative* links without relying on network or CI logs.

Scope:
- Scans Markdown files (".md") under the repo root.
- Extracts Markdown links and image links: [text](target) and ![alt](target)
- Checks only *relative/local* targets:
    - skips http(s), mailto:, tel:, data:
    - strips anchors (#...) and queries (?...) before checking
- Reports missing targets with source file + target.

This is intentionally simple and conservative. It will not fully parse every
Markdown edge case (nested parentheses, reference-style links, etc.), but it
covers the repo's common patterns.

Usage:
    python tools/check_local_links.py

Exit codes:
    0 - no broken local links
    1 - broken links found
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

# Matches inline Markdown links and images:
#   [text](target)
#   ![alt](target)
# This will not catch reference-style links: [text][ref]
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


@dataclass(frozen=True)
class BrokenLink:
    source: Path
    target: str


def is_external(target: str) -> bool:
    t = target.strip().lower()
    return t.startswith(("http://", "https://", "mailto:", "tel:", "data:"))


def normalize_target(target: str) -> str:
    # Strip anchors and querystrings
    t = target.strip()
    if "#" in t:
        t = t.split("#", 1)[0]
    if "?" in t:
        t = t.split("?", 1)[0]
    return t.strip()


def iter_markdown_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.md"):
        # Skip vendored/build artefacts if ever present
        parts = set(p.parts)
        if "site" in parts or ".venv" in parts or "node_modules" in parts:
            continue
        yield p


def find_broken_links(md_file: Path) -> list[BrokenLink]:
    try:
        text = md_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = md_file.read_text(encoding="utf-8", errors="ignore")

    broken: list[BrokenLink] = []

    for m in LINK_RE.finditer(text):
        raw = m.group(1).strip()
        if not raw:
            continue

        # Ignore pure anchors like (#section)
        if raw.startswith("#"):
            continue

        if is_external(raw):
            continue

        norm = normalize_target(raw)
        if not norm:
            continue

        # GitHub Markdown sometimes uses angle brackets: <path>
        if norm.startswith("<") and norm.endswith(">"):
            norm = norm[1:-1].strip()

        # Skip weird schemes or fragments
        if ":" in norm and not norm.startswith(("./", "../")):
            # e.g. "vscode://" or "obsidian://"; treat as external-ish
            continue

        src_dir = md_file.parent
        resolved = (src_dir / norm).resolve()

        # Prevent escaping the repo root (optional hardening)
        try:
            resolved.relative_to(ROOT)
        except ValueError:
            broken.append(BrokenLink(md_file, raw))
            continue

        # If link points to a directory, treat it as valid.
        # Rationale: GitHub renders directory targets as browseable paths,
        # and the repo deliberately uses some directory links (e.g. v1_core/).
        if resolved.is_dir():
            continue

        if not resolved.exists():
            broken.append(BrokenLink(md_file, raw))

    return broken


def main() -> int:
    md_files = list(iter_markdown_files(ROOT))
    all_broken: list[BrokenLink] = []

    for f in md_files:
        all_broken.extend(find_broken_links(f))

    if not all_broken:
        print("✅ No broken local relative links found")
        return 0

    print(f"❌ Broken local links: {len(all_broken)}\n")
    for b in all_broken:
        rel_src = b.source.relative_to(ROOT)
        print(f"- {rel_src} -> {b.target}")

    print("\nTip: fix the relative path or create the missing file.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
