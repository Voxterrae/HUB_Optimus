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
import re
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_REQUIREMENTS = REPO_ROOT / "requirements.txt"
DEVELOPMENT_REQUIREMENTS = REPO_ROOT / "requirements-dev.txt"
MIN_PYTHON = (3, 11)
SUPPORTED_PACKAGE_RANGES = {
    "jsonschema": ((4, 26, 0), (5, 0, 0)),
    "pytest": ((9, 1, 1), (10, 0, 0)),
}

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
    except ImportError:
        print(f"  [MISS] {name}")
        return False

    try:
        installed = metadata.version(name)
    except metadata.PackageNotFoundError:
        print(f"  [MISS] {name}")
        return False

    bounds = SUPPORTED_PACKAGE_RANGES.get(name)
    if bounds is None:
        print(f"  [OK]   {name} {installed}")
        return True

    match = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?(.*)$", installed)
    if match is None:
        print(f"  [MISS] {name} {installed} (unparseable version)")
        return False
    release = tuple(int(part or 0) for part in match.groups()[:3])
    suffix = match.group(4).lower()
    is_prerelease = bool(re.search(r"(?:a|b|rc|dev)\d", suffix))
    minimum, maximum = bounds
    ok = minimum <= release < maximum and not is_prerelease
    if ok:
        print(f"  [OK]   {name} {installed}")
        return True
    print(
        f"  [MISS] {name} {installed} "
        f"(need >= {'.'.join(map(str, minimum))}, < {maximum[0]})"
    )
    return False


def check_tool(name: str) -> bool:
    try:
        proc = subprocess.run(
            [name, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        print(f"  [MISS] {name}")
        return False
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
    with tempfile.TemporaryDirectory(prefix="hub-optimus-smoke-") as temp_dir:
        output_path = Path(temp_dir) / "example_scenario.result.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "run_scenario.py"),
                str(REPO_ROOT / "example_scenario.json"),
                "--output",
                str(output_path),
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
    if args.runtime_only:
        print("  [SKIP] git (not required by the runtime tier)")
    elif not check_tool("git"):
        print("\n   Git is required for the development tier.")
        return 1

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
