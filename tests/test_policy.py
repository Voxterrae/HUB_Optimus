"""Tests for the negotiation policy system."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_SCENARIO = REPO_ROOT / "run_scenario.py"
EXAMPLE = REPO_ROOT / "example_scenario.json"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(RUN_SCENARIO), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def _mixed_role_scenario(tmp_path: Path) -> Path:
    """Create a scenario with hardliner + mediator roles."""
    scenario = {
        "title": "Policy divergence test",
        "description": "Scenario with mixed roles to test biased policy.",
        "roles": [
            {"name": "Alpha", "role": "hardliner"},
            {"name": "Beta", "role": "mediator"},
            {"name": "Gamma", "role": "negotiator"},
        ],
        "success_criteria": {"offer": 5},
        "max_rounds": 10,
    }
    path = tmp_path / "mixed_roles.json"
    path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    return path


def test_uniform_policy_runs() -> None:
    proc = _run_cli("--scenario", str(EXAMPLE), "--seed", "42", "--policy", "uniform")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] in {"success", "failure"}


def test_biased_policy_runs() -> None:
    proc = _run_cli("--scenario", str(EXAMPLE), "--seed", "42", "--policy", "biased")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] in {"success", "failure"}


def test_no_policy_flag_backward_compatible() -> None:
    proc = _run_cli("--scenario", str(EXAMPLE), "--seed", "42")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] in {"success", "failure"}


def test_policy_changes_convergence_profile(tmp_path: Path) -> None:
    """Same seed + different policy + mixed roles → different offer history."""
    scenario_path = _mixed_role_scenario(tmp_path)
    proc_uniform = _run_cli(
        "--scenario", str(scenario_path), "--seed", "42", "--policy", "uniform",
    )
    proc_biased = _run_cli(
        "--scenario", str(scenario_path), "--seed", "42", "--policy", "biased",
    )
    assert proc_uniform.returncode == 0, proc_uniform.stderr
    assert proc_biased.returncode == 0, proc_biased.stderr

    payload_u = json.loads(proc_uniform.stdout)
    payload_b = json.loads(proc_biased.stdout)

    # At least one of: different history, different rounds, different status
    differs = (
        payload_u["history"] != payload_b["history"]
        or payload_u["rounds"] != payload_b["rounds"]
        or payload_u["status"] != payload_b["status"]
    )
    assert differs, (
        "Uniform and biased policies should produce different convergence profiles "
        "under the same seed when roles include hardliner/mediator"
    )


def test_each_policy_is_deterministic() -> None:
    """Same seed + same policy run twice → identical output."""
    for policy in ("uniform", "biased"):
        proc_a = _run_cli(
            "--scenario", str(EXAMPLE), "--seed", "99", "--policy", policy,
        )
        proc_b = _run_cli(
            "--scenario", str(EXAMPLE), "--seed", "99", "--policy", policy,
        )
        assert proc_a.returncode == 0, proc_a.stderr
        assert proc_b.returncode == 0, proc_b.stderr

        payload_a = json.loads(proc_a.stdout)
        payload_b = json.loads(proc_b.stdout)
        assert payload_a == payload_b, (
            f"Policy {policy!r} is not deterministic under seed 99"
        )
