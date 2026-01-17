#!/usr/bin/env python3
"""check_mirror.py

Integrity guard: if a directory is duplicated elsewhere (e.g., v1_core/ -> docs/v1_core/),
this script enforces that the duplicate is a byte-for-byte mirror.

Why: duplication is sometimes used for GitHub Pages / documentation routing, but it can drift.
This script turns drift into a CI failure.

Usage:
  python tools/check_mirror.py --pairs v1_core:docs/v1_core

Exit codes:
  0 = OK
  1 = mirror mismatch (missing/extra/different files)
  2 = config error
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EXCLUDE_DIRS = {
    ".git",
    ".github",
    "site",
    "__pycache__",
}

EXCLUDE_FILES = {
    ".DS_Store",
    "Thumbs.db",
}


@dataclass(frozen=True)
class Pair:
    src: Path
    dst: Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(root: Path) -> Iterable[Path]:
    """Yield file paths relative to root."""
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded dirs
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for fn in filenames:
            if fn in EXCLUDE_FILES:
                continue
            full = Path(dirpath) / fn
            rel = full.relative_to(root)
            yield rel


def parse_pairs(values: list[str]) -> list[Pair]:
    pairs: list[Pair] = []
    for v in values:
        if ":" not in v:
            raise ValueError(f"Invalid pair '{v}'. Expected format SRC:DST")
        src_s, dst_s = v.split(":", 1)
        src = Path(src_s).resolve()
        dst = Path(dst_s).resolve()
        pairs.append(Pair(src=src, dst=dst))
    return pairs


def compare_pair(pair: Pair, *, allow_missing_dst: bool) -> int:
    src, dst = pair.src, pair.dst

    if not src.exists() or not src.is_dir():
        print(f"[CONFIG] SRC directory not found: {src}")
        return 2

    if not dst.exists() or not dst.is_dir():
        msg = f"[WARN] DST directory not found: {dst}"
        if allow_missing_dst:
            print(msg + " (skipping; allow-missing-dst enabled)")
            return 0
        print(msg + " (failing)")
        return 1

    src_files = sorted(iter_files(src))
    dst_files = sorted(iter_files(dst))

    src_set = set(src_files)
    dst_set = set(dst_files)

    missing_in_dst = sorted(src_set - dst_set)
    extra_in_dst = sorted(dst_set - src_set)

    mismatched: list[Path] = []
    for rel in sorted(src_set & dst_set):
        src_path = src / rel
        dst_path = dst / rel

        # quick size check first
        try:
            if src_path.stat().st_size != dst_path.stat().st_size:
                mismatched.append(rel)
                continue
        except FileNotFoundError:
            mismatched.append(rel)
            continue

        if sha256_file(src_path) != sha256_file(dst_path):
            mismatched.append(rel)

    if not missing_in_dst and not extra_in_dst and not mismatched:
        print(f"[OK] Mirror clean: {src} -> {dst}")
        return 0

    print(f"[FAIL] Mirror mismatch: {src} -> {dst}")
    if missing_in_dst:
        print("  Missing in DST:")
        for p in missing_in_dst[:200]:
            print(f"    - {p}")
        if len(missing_in_dst) > 200:
            print(f"    ... ({len(missing_in_dst) - 200} more)")

    if extra_in_dst:
        print("  Extra in DST:")
        for p in extra_in_dst[:200]:
            print(f"    - {p}")
        if len(extra_in_dst) > 200:
            print(f"    ... ({len(extra_in_dst) - 200} more)")

    if mismatched:
        print("  Different content:")
        for p in mismatched[:200]:
            print(f"    - {p}")
        if len(mismatched) > 200:
            print(f"    ... ({len(mismatched) - 200} more)")

    return 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--pairs",
        nargs="+",
        required=True,
        help="Mirror pairs, format SRC:DST (example: v1_core:docs/v1_core)",
    )
    ap.add_argument(
        "--allow-missing-dst",
        action="store_true",
        help="If DST directory is missing, skip instead of failing.",
    )
    args = ap.parse_args(argv)

    try:
        pairs = parse_pairs(args.pairs)
    except ValueError as e:
        print(f"[CONFIG] {e}")
        return 2

    rc = 0
    for pair in pairs:
        r = compare_pair(pair, allow_missing_dst=args.allow_missing_dst)
        rc = max(rc, r)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
