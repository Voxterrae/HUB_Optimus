"""
Benchmark runner for deterministic narrative-risk reports.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BENCHMARKS_DIR = Path(__file__).resolve().parent
NARRATIVE_DIR = BENCHMARKS_DIR / "narrative"
INPUTS_DIR = NARRATIVE_DIR / "inputs"
EXPECTED_DIR = NARRATIVE_DIR / "expected"
REPO_ROOT = BENCHMARKS_DIR.parent
RUNNER = REPO_ROOT / "tools" / "render_narrative_report.py"


def run_case(input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(input_path),
            "--output",
            str(output_path),
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
    inputs = sorted(INPUTS_DIR.glob("*.json"))
    if not inputs:
        print("No narrative benchmark inputs found.", file=sys.stderr)
        return 1

    passed = 0
    failed = 0

    for input_path in inputs:
        label = input_path.stem
        expected_path = EXPECTED_DIR / f"{label}.md"
        if not expected_path.is_file():
            print(f"  FAIL  {label}  missing expected output")
            failed += 1
            continue

        actual_path = input_path.with_suffix(".actual.md")
        try:
            proc = run_case(input_path, actual_path)
            if proc.returncode != 0:
                print(f"  FAIL  {label}  renderer exited {proc.returncode}")
                print(f"        stderr: {proc.stderr.strip()}")
                failed += 1
                continue

            if actual_path.read_bytes() == expected_path.read_bytes():
                print(f"  PASS  {label}")
                passed += 1
            else:
                print(f"  FAIL  {label}  output differs from expected")
                failed += 1
        finally:
            if actual_path.exists():
                actual_path.unlink()

    total = passed + failed
    print(f"\n{passed} passed, {failed} failed, {total} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
