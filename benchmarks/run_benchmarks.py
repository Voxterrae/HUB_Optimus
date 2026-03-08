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


def parse_args() -> tuple[str | None, str | None]:
    name_filter = None
    summary_file = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--summary-file" and i + 1 < len(args):
            summary_file = args[i + 1]
            i += 2
        else:
            name_filter = args[i]
            i += 1
    return name_filter, summary_file


def main() -> int:
    name_filter, summary_file = parse_args()

    scenarios = sorted(SCENARIOS_DIR.glob("*.json"))
    if name_filter:
        scenarios = [s for s in scenarios if name_filter in s.stem]

    if not scenarios:
        print("No scenarios found.", file=sys.stderr)
        return 1

    passed = 0
    failed = 0
    results: list[tuple[str, str]] = []

    for scenario in scenarios:
        label = scenario.stem
        expected = EXPECTED_DIR / scenario.name

        if not expected.is_file():
            print(f"  SKIP  {label}  (no expected file)")
            results.append((label, "SKIP"))
            failed += 1
            continue

        actual = scenario.with_suffix(".actual.json")
        try:
            proc = run_benchmark(scenario, actual)
            if proc.returncode != 0:
                print(f"  FAIL  {label}  runner exited {proc.returncode}")
                print(f"        stderr: {proc.stderr.strip()}")
                results.append((label, "FAIL"))
                failed += 1
                continue

            expected_bytes = expected.read_bytes()
            actual_bytes = actual.read_bytes()

            if actual_bytes == expected_bytes:
                print(f"  PASS  {label}")
                results.append((label, "PASS"))
                passed += 1
            else:
                print(f"  FAIL  {label}  output differs from expected")
                results.append((label, "FAIL"))
                failed += 1
        finally:
            if actual.exists():
                actual.unlink()

    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")

    if summary_file:
        _write_summary(summary_file, results, passed, failed)

    return 0 if failed == 0 else 1


def _write_summary(
    path: str,
    results: list[tuple[str, str]],
    passed: int,
    failed: int,
) -> None:
    icon = {"PASS": "\u2705", "FAIL": "\u274c", "SKIP": "\u23ed\ufe0f"}
    lines = [
        "## Benchmark results\n",
        "| Scenario | Result |",
        "|---|---|",
    ]
    for label, status in results:
        lines.append(f"| `{label}` | {icon.get(status, '')} {status} |")
    lines.append("")
    lines.append(f"**{passed} passed, {failed} failed, {passed + failed} total**")
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
