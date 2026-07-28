#!/usr/bin/env python3
"""
check_mirror.py - Validate governance mirror structure and declared maturity

This script checks that:
1. Governance paths required by each declared language tier exist
2. Mirror maturity matches the versioned i18n manifest
3. Byte-identical English copies are declared as stubs, not translations
4. No git conflict markers exist in documentation files

Usage:
    python tools/check_mirror.py
    python tools/check_mirror.py --check-conflicts
    python tools/check_mirror.py --check-structure
    python tools/check_mirror.py --verbose
"""

import sys
import argparse
import re
import subprocess
from pathlib import Path
from typing import List

REPO_MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_MODULE_ROOT))

from tools.i18n_maturity import ManifestError, audit_repository, state_counts


class MirrorChecker:
    """Check governance document structure and declared maturity."""
    
    # Conflict marker patterns
    CONFLICT_MARKERS = [
        re.compile(r'^<{7}\s+HEAD', re.MULTILINE),
        re.compile(r'^={7}', re.MULTILINE),
        re.compile(r'^>{7}\s+', re.MULTILINE),
    ]
    
    def __init__(
        self,
        repo_root: str = None,
        verbose: bool = False,
        manifest_path: str = None,
    ):
        """
        Initialize the mirror checker.
        
        Args:
            repo_root: Path to repository root (default: auto-detect via git)
            verbose: Enable verbose output
            manifest_path: Optional path to the versioned maturity manifest
        """
        self.verbose = verbose
        self.repo_root = self._find_repo_root() if repo_root is None else Path(repo_root)
        if manifest_path is None:
            self.manifest_path = (
                self.repo_root / "docs" / "i18n" / "maturity.v1.json"
            )
        else:
            self.manifest_path = Path(manifest_path)
            if not self.manifest_path.is_absolute():
                self.manifest_path = self.repo_root / self.manifest_path
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def _find_repo_root(self) -> Path:
        """Find the repository root using git."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True,
                text=True,
                check=True
            )
            return Path(result.stdout.strip())
        except Exception:
            # Fallback to current directory
            return Path.cwd()
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{level}] {message}")
    
    def check_conflict_markers(self, paths: List[str] = None) -> int:
        """
        Check for git conflict markers in documentation files.
        
        Args:
            paths: List of paths to check (default: docs/)
            
        Returns:
            Number of files with conflict markers
        """
        if paths is None:
            paths = ["docs"]
        
        conflict_files = []
        
        for path_str in paths:
            search_path = self.repo_root / path_str
            if not search_path.exists():
                self.warnings.append(f"Path does not exist: {path_str}")
                continue
            
            # Find all markdown files
            md_files = search_path.rglob("*.md")
            
            for md_file in md_files:
                try:
                    content = md_file.read_text(encoding='utf-8')
                    has_conflict = False
                    
                    for pattern in self.CONFLICT_MARKERS:
                        if pattern.search(content):
                            has_conflict = True
                            break
                    
                    if has_conflict:
                        rel_path = md_file.relative_to(self.repo_root)
                        conflict_files.append(str(rel_path))
                        self.errors.append(f"Conflict markers found in: {rel_path}")
                        self.log(f"Found conflict markers in: {rel_path}", "ERROR")
                        
                except Exception as e:
                    self.warnings.append(f"Failed to read {md_file}: {e}")
        
        if conflict_files:
            print(f"\n❌ Found conflict markers in {len(conflict_files)} file(s):")
            for f in conflict_files:
                print(f"   - {f}")
        else:
            print("✅ No conflict markers found")
        
        return len(conflict_files)
    
    def check_governance_structure(self) -> int:
        """
        Check governance paths and maturity against the versioned manifest.

        Structural presence is not treated as evidence of linguistic parity.
        
        Returns:
            Number of structural or maturity issues found
        """
        try:
            result = audit_repository(
                self.repo_root,
                manifest_path=self.manifest_path,
                surfaces={"governance"},
            )
        except (ManifestError, OSError, UnicodeError) as exc:
            error = f"Governance maturity audit configuration error: {exc}"
            self.errors.append(error)
            print(f"❌ {error}")
            return 1

        governance = result.manifest["surfaces"]["governance"]
        print(f"\n📋 Versioned governance files: {len(governance['files'])}")
        counts = state_counts(result.observations)
        for locale, metadata in result.manifest["locales"].items():
            locale_counts = counts.get(locale, {})
            details = ", ".join(
                f"{state}={count}" for state, count in sorted(locale_counts.items())
            )
            print(
                f"   {locale} ({metadata['direction']}, "
                f"tier={metadata['tier']}): {details}"
            )

        self.errors.extend(result.errors)
        self.warnings.extend(result.warnings)

        if result.errors:
            print(f"\n❌ Governance maturity issues ({len(result.errors)}):")
            for error in result.errors:
                print(f"   - {error}")
        else:
            print(
                "✅ Required governance paths exist and maturity declarations "
                "match observed content"
            )
            print("ℹ️  Structural presence does not certify linguistic parity")

        if result.warnings:
            print("\n⚠️  Governance maturity warnings:")
            for warning in result.warnings:
                print(f"   - {warning}")

        return len(result.errors)
    
    def run_all_checks(self) -> bool:
        """
        Run all checks.
        
        Returns:
            True if all checks pass, False otherwise
        """
        print("=" * 60)
        print("HUB_Optimus Mirror Checker")
        print("=" * 60)
        print(f"Repository: {self.repo_root}")
        print()
        
        # Check for conflict markers
        print("1. Checking for conflict markers...")
        conflicts = self.check_conflict_markers()
        print()
        
        # Check governance structure
        print("2. Checking governance file structure...")
        structure_issues = self.check_governance_structure()
        print()
        
        # Summary
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        
        total_errors = len(self.errors)
        total_warnings = len(self.warnings)
        
        if total_errors == 0:
            print("✅ All checks passed!")
            if total_warnings > 0:
                print(f"⚠️  {total_warnings} warning(s)")
        else:
            print(f"❌ {total_errors} error(s) found")
            if total_warnings > 0:
                print(f"⚠️  {total_warnings} warning(s)")
        
        return total_errors == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check governance document mirroring and consistency"
    )
    parser.add_argument(
        "--check-conflicts",
        action="store_true",
        help="Only check for conflict markers"
    )
    parser.add_argument(
        "--check-structure",
        action="store_true",
        help="Only check governance file structure"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Repository root path (default: auto-detect)"
    )
    parser.add_argument(
        "--manifest",
        type=str,
        help="Maturity manifest path (default: docs/i18n/maturity.v1.json)"
    )
    
    args = parser.parse_args()
    
    checker = MirrorChecker(
        repo_root=args.repo_root,
        verbose=args.verbose,
        manifest_path=args.manifest,
    )
    
    # Run specific checks or all checks
    if args.check_conflicts:
        conflicts = checker.check_conflict_markers()
        sys.exit(0 if conflicts == 0 else 1)
    elif args.check_structure:
        issues = checker.check_governance_structure()
        sys.exit(0 if issues == 0 else 1)
    else:
        success = checker.run_all_checks()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
