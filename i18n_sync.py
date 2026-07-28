"""Audit declared documentation translation maturity.

The audit is policy-aware.  It checks only the onboarding and governance files
versioned in ``docs/i18n/maturity.v1.json`` and applies each locale's declared
coverage tier.  A green result means that declarations match repository evidence;
it is not a claim that every file is translated or professionally reviewed.

Usage:
    python i18n_sync.py
    python i18n_sync.py --docs-dir docs
    python i18n_sync.py --manifest docs/i18n/maturity.v1.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.i18n_maturity import (
    AuditResult,
    ManifestError,
    audit_repository,
    state_counts,
)


def _display_summary(result: AuditResult) -> None:
    manifest = result.manifest
    policy = manifest["policy"]
    counts = state_counts(result.observations)

    print("HUB_Optimus translation maturity audit")
    print(f"Manifest version: {manifest['manifest_version']}")
    print(
        "Policy: "
        f"v1 canonical={policy['canonical_v1']}; "
        f"parity target={policy['parity_target_v1']}; "
        f"docs baseline={policy['docs_structural_baseline']}"
    )
    print()

    for locale, metadata in manifest["locales"].items():
        locale_counts = counts.get(locale, {})
        details = ", ".join(
            f"{state}={count}" for state, count in sorted(locale_counts.items())
        )
        print(
            f"- {locale} ({metadata['direction']}, tier={metadata['tier']}): "
            f"{details or 'no declared files'}"
        )

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.errors:
        print("\nErrors:", file=sys.stderr)
        for error in result.errors:
            print(f"  - {error}", file=sys.stderr)
        print(
            "\nFAILED: maturity declarations or tier requirements do not match "
            "repository evidence.",
            file=sys.stderr,
        )
    else:
        print(
            "\nPASS: declarations match repository evidence and every "
            "tier-required file exists."
        )
        print("This result does not certify linguistic parity.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit documentation against the versioned i18n maturity policy."
    )
    parser.add_argument(
        "--docs-dir",
        "--docs_dir",
        dest="docs_dir",
        default="docs",
        help="Documentation root containing the manifest and locale directories.",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Maturity manifest path (default: <docs-dir>/i18n/maturity.v1.json).",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    docs_dir = Path(args.docs_dir)
    if not docs_dir.is_absolute():
        docs_dir = repo_root / docs_dir
    if not docs_dir.is_dir():
        print(f"Documentation directory not found: {docs_dir}", file=sys.stderr)
        raise SystemExit(2)

    manifest_path = Path(args.manifest) if args.manifest else None
    if manifest_path is not None and not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path

    try:
        result = audit_repository(
            repo_root,
            docs_dir=docs_dir,
            manifest_path=manifest_path,
        )
    except (ManifestError, OSError, UnicodeError) as exc:
        print(f"Translation maturity audit configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    _display_summary(result)
    raise SystemExit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
