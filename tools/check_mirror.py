#!/usr/bin/env python3
"""
check_mirror.py - Validate governance document mirroring across languages

This script checks that:
1. Governance documents are properly mirrored across all language directories
2. No git conflict markers exist in documentation files
3. File structure is consistent across language mirrors

Usage:
    python tools/check_mirror.py
    python tools/check_mirror.py --check-conflicts
    python tools/check_mirror.py --check-structure
    python tools/check_mirror.py --verbose
"""

import os
import sys
import argparse
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple


class MirrorChecker:
    """Check governance document mirroring and consistency."""
    
    # Conflict marker patterns
    CONFLICT_MARKERS = [
        re.compile(r'^<{7}\s+HEAD', re.MULTILINE),
        re.compile(r'^={7}', re.MULTILINE),
        re.compile(r'^>{7}\s+', re.MULTILINE),
    ]
    
    # Canonical governance directory
    CANONICAL_DIR = "docs/governance"
    
    # Language codes to check (subdirectories of docs/)
    LANGUAGE_DIRS = ["de", "es", "fr", "ca", "ru"]
    
    def __init__(self, repo_root: str = None, verbose: bool = False):
        """
        Initialize the mirror checker.
        
        Args:
            repo_root: Path to repository root (default: auto-detect via git)
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.repo_root = self._find_repo_root() if repo_root is None else Path(repo_root)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def _find_repo_root(self) -> Path:
        """Find the repository root using git."""
        try:
            import subprocess
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
        Check that governance files are mirrored across all language directories.
        
        Returns:
            Number of structural issues found
        """
        canonical_path = self.repo_root / self.CANONICAL_DIR
        
        if not canonical_path.exists():
            self.errors.append(f"Canonical directory does not exist: {self.CANONICAL_DIR}")
            print(f"❌ Canonical directory not found: {self.CANONICAL_DIR}")
            return 1
        
        # Get list of files in canonical directory
        canonical_files = set()
        for f in canonical_path.glob("*.md"):
            canonical_files.add(f.name)
        
        if not canonical_files:
            self.warnings.append("No markdown files found in canonical governance directory")
            print("⚠️  No markdown files in canonical governance directory")
            return 0
        
        self.log(f"Found {len(canonical_files)} files in canonical directory", "INFO")
        print(f"\n📋 Canonical governance files: {len(canonical_files)}")
        
        issues = 0
        missing_by_lang: Dict[str, List[str]] = {}
        extra_by_lang: Dict[str, List[str]] = {}
        
        # Check each language directory
        for lang in self.LANGUAGE_DIRS:
            lang_gov_path = self.repo_root / "docs" / lang / "governance"
            
            if not lang_gov_path.exists():
                self.errors.append(f"Language governance directory missing: {lang}/governance")
                print(f"❌ Missing directory: docs/{lang}/governance")
                issues += 1
                missing_by_lang[lang] = list(canonical_files)
                continue
            
            # Get files in this language's governance directory
            lang_files = set()
            for f in lang_gov_path.glob("*.md"):
                lang_files.add(f.name)
            
            # Find missing files
            missing = canonical_files - lang_files
            if missing:
                missing_by_lang[lang] = sorted(missing)
                for filename in missing:
                    self.errors.append(f"Missing mirror: docs/{lang}/governance/{filename}")
                    issues += 1
            
            # Find extra files (not in canonical)
            extra = lang_files - canonical_files
            if extra:
                extra_by_lang[lang] = sorted(extra)
                for filename in extra:
                    self.warnings.append(f"Extra file (not in canonical): docs/{lang}/governance/{filename}")
        
        # Report results
        if issues == 0 and not extra_by_lang:
            print("✅ All governance files properly mirrored across languages")
        else:
            if missing_by_lang:
                print(f"\n❌ Missing mirrors found ({issues} issues):")
                for lang, files in missing_by_lang.items():
                    print(f"\n   {lang}/ ({len(files)} missing):")
                    for f in files:
                        print(f"     - {f}")
            
            if extra_by_lang:
                print(f"\n⚠️  Extra files (not in canonical):")
                for lang, files in extra_by_lang.items():
                    print(f"\n   {lang}/ ({len(files)} extra):")
                    for f in files:
                        print(f"     - {f}")
        
        return issues
    
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
    
    args = parser.parse_args()
    
    checker = MirrorChecker(repo_root=args.repo_root, verbose=args.verbose)
    
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
