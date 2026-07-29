"""Regression tests for tri-state, axis-aware boundary search."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tools import scenario_boundary_search as boundary_search
from tools.scenario_generator.generate_scenarios import generate


REPO_ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_SEARCH = REPO_ROOT / "tools" / "scenario_boundary_search.py"


def _default_base_scenarios() -> dict[str, dict]:
    """Return the first scenario per family from the default generated set."""
    bases: dict[str, dict] = {}
    for _stem, family, scenario in generate(count=60, seed=42):
        bases.setdefault(family, scenario)
    return bases


@pytest.mark.parametrize("family", ["info_asymmetry", "resource_scarcity"])
def test_seed_2_threshold_boundary_matches_exhaustive_states(family: str) -> None:
    scenario = _default_base_scenarios()[family]

    boundary, states = boundary_search.find_max_stable_with_states(
        scenario,
        boundary_search.set_threshold,
        1,
        5,
        "2",
        axis="threshold",
    )

    assert states == {
        "1": "success",
        "2": "success",
        "3": "success",
        "4": "failure",
        "5": "success",
    }
    successful_values = [
        int(value) for value, state in states.items() if state == "success"
    ]
    assert boundary == max(successful_values) == 5


def test_biased_actor_boundary_is_exhaustive_and_non_monotonic(
    monkeypatch,
) -> None:
    scenario = _default_base_scenarios()["incentive_misalignment"]
    monkeypatch.setattr(boundary_search, "ACTIVE_POLICY", "biased")

    boundary, states = boundary_search.find_min_stable_with_states(
        scenario,
        boundary_search.set_actors,
        1,
        6,
        "11",
        axis="actors",
    )

    assert states == {
        "1": "failure",
        "2": "failure",
        "3": "success",
        "4": "success",
        "5": "success",
        "6": "failure",
    }
    assert boundary == 3

    verification = boundary_search.verify_boundary_min(
        scenario,
        boundary_search.set_actors,
        None,
        1,
        6,
        "11",
        axis="actors",
    )
    assert verification["exhaustive_boundary"] == 3
    assert verification["valid"] is False


def test_minimum_verification_checks_every_lower_value(monkeypatch) -> None:
    states = {
        1: "failure",
        2: "success",
        3: "failure",
        4: "success",
        5: "success",
        6: "success",
    }
    monkeypatch.setattr(
        boundary_search,
        "_probe_state",
        lambda _scenario, _seed, *, axis, value: states[value],
    )

    verification = boundary_search.verify_boundary_min(
        {},
        lambda _base, value: value,
        4,
        1,
        6,
        "7",
        axis="actors",
    )

    assert verification["exhaustive_boundary"] == 2
    assert verification["below_fails"] is False
    assert verification["valid"] is False


def test_probe_error_cannot_become_failure_observation(monkeypatch) -> None:
    scenario = _default_base_scenarios()["info_asymmetry"]

    monkeypatch.setattr(
        boundary_search,
        "probe_detail",
        lambda _scenario, _seed: {
            "status": "error",
            "rounds": None,
            "error": "runner unavailable",
        },
    )

    assert boundary_search.probe(scenario, "1") == "error"
    with pytest.raises(boundary_search.ProbeExecutionError, match="runner unavailable"):
        boundary_search.find_max_stable(
            scenario,
            boundary_search.set_threshold,
            1,
            5,
            "1",
            axis="threshold",
        )


def test_invalid_policy_is_rejected_by_boundary_cli() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(BOUNDARY_SEARCH),
            "--policy",
            "not-implemented",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert proc.returncode == 2
    assert "invalid choice" in proc.stderr
    assert "biased" in proc.stderr
    assert "uniform" in proc.stderr


def test_boundary_results_include_method_and_policy_provenance(
    monkeypatch,
) -> None:
    scenario = _default_base_scenarios()["info_asymmetry"]

    monkeypatch.setattr(boundary_search, "ACTIVE_POLICY", None)
    monkeypatch.setattr(
        boundary_search,
        "_probe_state",
        lambda _scenario, _seed, *, axis, value: "success",
    )

    results = boundary_search.search_boundaries(
        [("info_asymmetry_001", "info_asymmetry", scenario)],
        "7",
    )
    entry = results["info_asymmetry"]

    assert entry["seed"] == 7
    assert entry["policy"] == "simulator_default"
    assert entry["methods"] == {
        "rounds_min": "binary_search",
        "actors_min": "exhaustive_enumeration",
        "threshold_max": "exhaustive_enumeration",
    }
    assert entry["actors_probe_states"] == {
        str(value): "success" for value in range(1, 7)
    }
    assert entry["threshold_probe_states"] == {
        str(value): "success" for value in range(1, 6)
    }
