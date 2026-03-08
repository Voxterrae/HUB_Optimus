"""
Benchmark runner for HUB_Optimus.

Executes every scenario in benchmarks/scenarios/ through run_scenario.py
with seed 42 and compares the output byte-for-byte against the
corresponding file in benchmarks/expected/.

Exit codes:
  0  all benchmarks match
  1  at least one mismatch or missing expected file

Usage:
  python benchmarks/run_benchmarks.py          # run all
  python benchmarks/run_benchmarks.py basic     # run only scenarios containing "basic"
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BENCHMARKS_DIR = Path(__file__).resolve().parent
SCENARIOS_DIR = BENCHMARKS_DIR / "scenarios"
EXPECTED_DIR = BENCHMARKS_DIR / "expected"
REPO_ROOT = BENCHMARKS_DIR.parent
RUNNER = REPO_ROOT / "run_scenario.py"
SEED = "42"


def run_benchmark(scenario: Path, actual_output: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(scenario),
            "--output",
            str(actual_output),
            "--seed",
            SEED,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def main() -> int:
    name_filter = sys.argv[1] if len(sys.argv) > 1 else None

    scenarios = sorted(SCENARIOS_DIR.glob("*.json"))
    if name_filter:
        scenarios = [s for s in scenarios if name_filter in s.stem]

    if not scenarios:
        print("No scenarios found.", file=sys.stderr)
        return 1

    passed = 0
    failed = 0

    for scenario in scenarios:
        label = scenario.stem
        expected = EXPECTED_DIR / scenario.name

        if not expected.is_file():
            print(f"  SKIP  {label}  (no expected file)")
            failed += 1
            continue

        actual = scenario.with_suffix(".actual.json")
        try:
            proc = run_benchmark(scenario, actual)
            if proc.returncode != 0:
                print(f"  FAIL  {label}  runner exited {proc.returncode}")
                print(f"        stderr: {proc.stderr.strip()}")
                failed += 1
                continue

            expected_bytes = expected.read_bytes()
            actual_bytes = actual.read_bytes()

            if actual_bytes == expected_bytes:
                print(f"  PASS  {label}")
                passed += 1
            else:
                print(f"  FAIL  {label}  output differs from expected")
                failed += 1
        finally:
            if actual.exists():
                actual.unlink()

    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
