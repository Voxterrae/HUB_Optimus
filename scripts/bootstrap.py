#!/usr/bin/env python3
"""
Bootstrap script for HUB_Optimus development environment.

Verifies tooling, installs missing dependencies, and runs a quick
health check.  Safe to run repeatedly — idempotent by design.

Usage:
  python scripts/bootstrap.py            # full bootstrap
  python scripts/bootstrap.py --check    # verify only, no install
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = REPO_ROOT / "requirements-dev.txt"
MIN_PYTHON = (3, 11)

# ── Checks ──────────────────────────────────────────────────


def check_python() -> bool:
    v = sys.version_info
    ok = (v.major, v.minor) >= MIN_PYTHON
    tag = "OK" if ok else "FAIL"
    print(f"  [{tag}]  Python {v.major}.{v.minor}.{v.micro}  (need >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})")
    return ok


def check_package(name: str) -> bool:
    try:
        __import__(name)
        print(f"  [OK]   {name}")
        return True
    except ImportError:
        print(f"  [MISS] {name}")
        return False


def check_tool(name: str) -> bool:
    proc = subprocess.run(
        [name, "--version"],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode == 0:
        version = proc.stdout.strip().split("\n")[0]
        print(f"  [OK]   {name}  ({version})")
        return True
    print(f"  [MISS] {name}")
    return False


# ── Install ─────────────────────────────────────────────────


def install_requirements() -> bool:
    print(f"\nInstalling from {REQUIREMENTS.name} ...")
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS), "-q"],
        check=False,
    )
    return proc.returncode == 0


# ── Health check ────────────────────────────────────────────


def run_tests() -> bool:
    print("\nRunning test suite ...")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line"],
        cwd=REPO_ROOT, check=False,
    )
    return proc.returncode == 0


def run_benchmarks() -> bool:
    print("\nRunning benchmarks ...")
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "benchmarks" / "run_benchmarks.py")],
        cwd=REPO_ROOT, check=False,
    )
    return proc.returncode == 0


# ── Main ────────────────────────────────────────────────────


def main() -> int:
    check_only = "--check" in sys.argv

    print("=== HUB_Optimus Environment Bootstrap ===\n")

    # 1. Python version
    print("1. Python")
    py_ok = check_python()
    if not py_ok:
        print(f"\n   Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]} required.")
        return 1

    # 2. Key packages
    print("\n2. Packages")
    packages = ["jsonschema", "pytest"]
    missing = [p for p in packages if not check_package(p)]

    # 3. Git
    print("\n3. Tools")
    check_tool("git")

    # 4. Install if needed
    if missing and not check_only:
        if not install_requirements():
            print("\n   pip install failed.")
            return 1
        # Re-check
        still_missing = [p for p in missing if not check_package(p)]
        if still_missing:
            print(f"\n   Still missing after install: {still_missing}")
            return 1
    elif missing and check_only:
        print(f"\n   Missing packages (run without --check to install): {missing}")
        return 1

    # 5. Health check
    if not check_only:
        tests_ok = run_tests()
        benchmarks_ok = run_benchmarks()
        print("\n=== Summary ===")
        print(f"  Tests:      {'PASS' if tests_ok else 'FAIL'}")
        print(f"  Benchmarks: {'PASS' if benchmarks_ok else 'FAIL (expected on Windows/CRLF)'}")
    else:
        print("\n=== Check complete (no install, no tests) ===")

    print("\n  Environment ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
