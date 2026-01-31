"""
Script to audit and synchronize translations in the HUB_Optimus documentation.

This tool compares the set of English documentation files with the available translations
in each language directory under ``docs``.  It reports missing translations, helping
contributors keep all language versions up to date with the English source.

Usage:
    python i18n_sync.py --docs-dir docs

The default ``docs`` directory is used if no argument is provided.  The script prints a
summary of missing files for each language directory found (two‑letter ISO codes) and
returns a non‑zero exit status if any missing translations are detected.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List


def gather_english_files(base_dir: str, languages: List[str]) -> List[str]:
    """Collect relative paths of all English documentation files.

    This function traverses ``base_dir`` and returns a list of relative file paths for
    Markdown files that are part of the English source (i.e. not located in language
    subdirectories).  It skips directories named with two‑letter codes defined in
    ``languages``.

    Args:
        base_dir: The root documentation directory (e.g. ``docs``).
        languages: A list of two‑letter language folder names to skip.

    Returns:
        A list of relative file paths for English Markdown files.
    """
    english_files: List[str] = []
    for root, dirs, files in os.walk(base_dir):
        # Skip traversing into language directories at the first level
        rel_root = os.path.relpath(root, base_dir)
        parts = rel_root.split(os.sep)
        if parts[0] in languages:
            continue
        for filename in files:
            if filename.lower().endswith(".md"):
                rel_path = os.path.relpath(os.path.join(root, filename), base_dir)
                english_files.append(rel_path)
    return english_files


def audit_translations(docs_dir: str) -> Dict[str, List[str]]:
    """Detect missing translation files relative to the English documentation.

    Args:
        docs_dir: The root documentation directory.

    Returns:
        A dictionary mapping each language code to a list of missing file paths.
    """
    # Language directories are top‑level subdirectories with two letters (e.g. 'es', 'fr')
    langs = [d for d in os.listdir(docs_dir) if os.path.isdir(os.path.join(docs_dir, d)) and len(d) == 2]
    english_files = gather_english_files(docs_dir, langs)
    missing: Dict[str, List[str]] = {lang: [] for lang in langs}
    for file_rel in english_files:
        # Skip comparing English files that already live inside a language directory (shouldn't happen)
        parts = file_rel.split(os.sep)
        if parts[0] in langs:
            continue
        for lang in langs:
            translated_path = os.path.join(docs_dir, lang, file_rel)
            if not os.path.isfile(translated_path):
                missing[lang].append(file_rel)
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(description="Check documentation translations against the English source.")
    parser.add_argument(
        "--docs-dir",
        dest="docs_dir",
        default="docs",
        help="Path to the documentation directory containing language subfolders.",
    )
    args = parser.parse_args()
    docs_dir = args.docs_dir
    if not os.path.isdir(docs_dir):
        print(f"Documentation directory not found: {docs_dir}", file=sys.stderr)
        sys.exit(2)
    missing = audit_translations(docs_dir)
    any_missing = False
    for lang, files in sorted(missing.items()):
        if files:
            any_missing = True
            print(f"Missing translations for '{lang}':")
            for f in files:
                print(f"  - {f}")
        else:
            print(f"All files translated for '{lang}'.")
    if any_missing:
        sys.exit(1)


if __name__ == "__main__":
    main()