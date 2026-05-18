"""
Benchmark runner for HUB_Optimus.

Executes every scenario in benchmarks/scenarios/ through run_scenario.py
with seed 42 and compares the output byte-for-byte against the
corresponding file in benchmarks/expected/.

Additionally performs structural drift analysis comparing outcome, round
count, and actor count between expected and actual results, classifying
each difference by severity (info / warning / critical).

Exit codes:
  0  all benchmarks match (byte-level)
  1  at least one mismatch or missing expected file

Usage:
  python benchmarks/run_benchmarks.py                       # run all
  python benchmarks/run_benchmarks.py basic                 # filter by name
  python benchmarks/run_benchmarks.py --summary-file FILE   # write Markdown summary
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

BENCHMARKS_DIR = Path(__file__).resolve().parent
SCENARIOS_DIR = BENCHMARKS_DIR / "scenarios"
EXPECTED_DIR = BENCHMARKS_DIR / "expected"
GENERATED_DIR = BENCHMARKS_DIR.parent / "scenarios" / "generated"
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


def parse_args() -> tuple[str | None, str | None, bool]:
    name_filter = None
    summary_file = None
    include_generated = False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--summary-file" and i + 1 < len(args):
            summary_file = args[i + 1]
            i += 2
        elif args[i] == "--include-generated":
            include_generated = True
            i += 1
        else:
            name_filter = args[i]
            i += 1
    return name_filter, summary_file, include_generated


def main() -> int:
    name_filter, summary_file, include_generated = parse_args()

    scenarios = sorted(SCENARIOS_DIR.glob("*.json"))
    if include_generated and GENERATED_DIR.is_dir():
        scenarios.extend(sorted(GENERATED_DIR.rglob("*.json")))
    if name_filter:
        scenarios = [s for s in scenarios if name_filter in s.stem]

    if not scenarios:
        print("No scenarios found.", file=sys.stderr)
        return 1

    passed = 0
    failed = 0
    results: list[tuple[str, str]] = []
    drift_rows: list[DriftRow] = []

    for scenario in scenarios:
        label = scenario.stem
        expected = EXPECTED_DIR / scenario.name
        is_generated = not expected.is_file()

        if is_generated and not include_generated:
            print(f"  SKIP  {label}  (no expected file)")
            results.append((label, "SKIP"))
            drift_rows.append(DriftRow(label))
            failed += 1
            continue

        actual = scenario.with_suffix(".actual.json")
        try:
            proc = run_benchmark(scenario, actual)
            if proc.returncode != 0:
                print(f"  FAIL  {label}  runner exited {proc.returncode}")
                print(f"        stderr: {proc.stderr.strip()}")
                results.append((label, "FAIL"))
                drift_rows.append(DriftRow(label))
                failed += 1
                continue

            if is_generated:
                # Generated scenarios: smoke test only (runner exited 0)
                print(f"  RUN   {label}")
                results.append((label, "RUN"))
                drift_rows.append(DriftRow(label))
                passed += 1
                continue

            expected_bytes = expected.read_bytes()
            actual_bytes = actual.read_bytes()
            bytes_match = actual_bytes == expected_bytes

            if bytes_match:
                print(f"  PASS  {label}")
                results.append((label, "PASS"))
                passed += 1
            else:
                print(f"  FAIL  {label}  output differs from expected")
                results.append((label, "FAIL"))
                failed += 1

            drift_rows.append(
                _analyze_drift(label, expected_bytes, actual_bytes, bytes_match)
            )
        finally:
            if actual.exists():
                actual.unlink()

    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")

    if summary_file:
        _write_summary(summary_file, results, passed, failed, drift_rows)

    return 0 if failed == 0 else 1


# ── Drift analysis ──────────────────────────────────────────


class DriftRow:
    """Structural comparison results for one benchmark scenario."""

    __slots__ = (
        "label", "bytes_match",
        "expected_status", "actual_status",
        "expected_rounds", "actual_rounds",
        "expected_actors", "actual_actors",
        "severity", "notes",
    )

    def __init__(self, label: str) -> None:
        self.label = label
        self.bytes_match: bool | None = None
        self.expected_status: str | None = None
        self.actual_status: str | None = None
        self.expected_rounds: int | None = None
        self.actual_rounds: int | None = None
        self.expected_actors: int | None = None
        self.actual_actors: int | None = None
        self.severity: str = "skip"
        self.notes: str = ""


def _actor_count(data: dict[str, Any]) -> int | None:
    """Return the number of distinct actors from the first round of history."""
    history = data.get("history")
    if not isinstance(history, list) or not history:
        return None
    first_round = history[0]
    if isinstance(first_round, dict):
        return len(first_round)
    return None


def _analyze_drift(
    label: str,
    expected_bytes: bytes,
    actual_bytes: bytes,
    bytes_match: bool,
) -> DriftRow:
    """Compare expected vs actual JSON structurally and classify severity."""
    row = DriftRow(label)
    row.bytes_match = bytes_match

    try:
        exp = json.loads(expected_bytes)
        act = json.loads(actual_bytes)
    except (json.JSONDecodeError, ValueError):
        row.severity = "critical"
        row.notes = "JSON parse error"
        return row

    row.expected_status = exp.get("status")
    row.actual_status = act.get("status")
    row.expected_rounds = exp.get("rounds")
    row.actual_rounds = act.get("rounds")
    row.expected_actors = _actor_count(exp)
    row.actual_actors = _actor_count(act)

    if bytes_match:
        row.severity = "info"
        row.notes = "stable"
        return row

    issues: list[str] = []

    if row.expected_status != row.actual_status:
        row.severity = "critical"
        if row.actual_status == "success" and row.expected_status == "failure":
            issues.append("false positive agreement")
        elif row.actual_status == "failure" and row.expected_status == "success":
            issues.append("lost agreement")
        else:
            issues.append("outcome changed")

    if row.expected_rounds != row.actual_rounds:
        if row.severity != "critical":
            row.severity = "warning"
        if (row.actual_rounds or 0) > (row.expected_rounds or 0):
            issues.append("slower convergence")
        else:
            issues.append("faster convergence")

    if row.expected_actors != row.actual_actors:
        if row.severity != "critical":
            row.severity = "warning"
        issues.append("actor count changed")

    if not issues:
        row.severity = "info"
        issues.append("formatting diff only")

    row.notes = "; ".join(issues)
    return row


# ── Summary output ──────────────────────────────────────────


def _write_summary(
    path: str,
    results: list[tuple[str, str]],
    passed: int,
    failed: int,
    drift_rows: list[DriftRow],
) -> None:
    icon = {"PASS": "\u2705", "FAIL": "\u274c", "SKIP": "\u23ed\ufe0f", "RUN": "\U0001f504"}
    sev_icon = {"info": "\U0001f7e2", "warning": "\U0001f7e1", "critical": "\U0001f534", "skip": "\u23ed\ufe0f"}
    lines = [
        "## Benchmark results\n",
        "| Scenario | Result |",
        "|---|---|",
    ]
    for label, status in results:
        lines.append(f"| `{label}` | {icon.get(status, '')} {status} |")
    lines.append("")
    lines.append(f"**{passed} passed, {failed} failed, {passed + failed} total**")

    # Drift analysis table (only when there are analysed rows)
    analysed = [r for r in drift_rows if r.severity != "skip"]
    if analysed:
        lines.append("")
        lines.append("### Structural drift analysis\n")
        lines.append("| Scenario | Outcome | Rounds | Actors | Severity | Notes |")
        lines.append("|---|---|---|---|---|---|")
        for r in analysed:
            outcome = _drift_cell(r.expected_status, r.actual_status)
            rounds = _drift_cell(r.expected_rounds, r.actual_rounds)
            actors = _drift_cell(r.expected_actors, r.actual_actors)
            sev = f"{sev_icon.get(r.severity, '')} {r.severity}"
            lines.append(f"| `{r.label}` | {outcome} | {rounds} | {actors} | {sev} | {r.notes} |")

    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _drift_cell(expected: Any, actual: Any) -> str:
    """Format a drift table cell showing expected vs actual if they differ."""
    if expected is None and actual is None:
        return "-"
    if expected == actual:
        return str(expected)
    return f"{expected} \u2192 {actual}"


if __name__ == "__main__":
    raise SystemExit(main())
