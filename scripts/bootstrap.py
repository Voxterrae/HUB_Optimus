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

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_REQUIREMENTS = REPO_ROOT / "requirements.txt"
DEVELOPMENT_REQUIREMENTS = REPO_ROOT / "requirements-dev.txt"
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


def install_requirements(requirements: Path) -> bool:
    """Install one explicit dependency tier."""
    print(f"\nInstalling from {requirements.name} ...")
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements), "-q"],
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


def run_runtime_smoke() -> bool:
    """Run the documented scenario CLI without development-only packages."""
    print("\nRunning runtime smoke test ...")
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "run_scenario.py"),
            str(REPO_ROOT / "example_scenario.json"),
            "--seed",
            "42",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        diagnostic = proc.stderr.strip() or proc.stdout.strip() or "no diagnostic"
        print(f"  [FAIL] runtime smoke: {diagnostic}")
        return False
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"  [FAIL] runtime smoke returned invalid JSON: {exc}")
        return False
    ok = (
        payload.get("status") in {"success", "failure"}
        and isinstance(payload.get("rounds"), int)
        and isinstance(payload.get("history"), list)
    )
    print(f"  [{'OK' if ok else 'FAIL'}]   scenario CLI")
    return ok


# ── Main ────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare or verify a HUB_Optimus Python environment."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the selected dependency tier without installing or running tests.",
    )
    parser.add_argument(
        "--runtime-only",
        action="store_true",
        help=(
            "Install/check requirements.txt and run only the scenario CLI smoke test; "
            "do not require pytest."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    check_only = args.check
    requirements = (
        RUNTIME_REQUIREMENTS if args.runtime_only else DEVELOPMENT_REQUIREMENTS
    )

    print("=== HUB_Optimus Environment Bootstrap ===\n")
    print(
        "Mode: "
        f"{'runtime' if args.runtime_only else 'development'} "
        f"({requirements.name})"
    )

    # 1. Python version
    print("1. Python")
    py_ok = check_python()
    if not py_ok:
        print(f"\n   Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]} required.")
        return 1

    # 2. Key packages
    print("\n2. Packages")
    packages = ["jsonschema"] if args.runtime_only else ["jsonschema", "pytest"]
    missing = [p for p in packages if not check_package(p)]

    # 3. Git
    print("\n3. Tools")
    check_tool("git")

    # 4. Install if needed
    if missing and not check_only:
        if not install_requirements(requirements):
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
        if args.runtime_only:
            smoke_ok = run_runtime_smoke()
            print("\n=== Summary ===")
            print(f"  Runtime smoke: {'PASS' if smoke_ok else 'FAIL'}")
            if not smoke_ok:
                return 1
        else:
            tests_ok = run_tests()
            benchmarks_ok = run_benchmarks()
            print("\n=== Summary ===")
            print(f"  Tests:      {'PASS' if tests_ok else 'FAIL'}")
            print(f"  Benchmarks: {'PASS' if benchmarks_ok else 'FAIL'}")
            if not tests_ok or not benchmarks_ok:
                return 1
    else:
        print("\n=== Check complete (no install, no tests) ===")

    print("\n  Environment ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
