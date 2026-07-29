from __future__ import annotations

import copy
import random

from hub_optimus_simulator import Scenario, Simulator


def _scenario() -> Scenario:
    return Scenario(
        title="Isolation contract",
        description="Exercise deterministic simulator state boundaries.",
        roles=[
            {"name": "Alpha", "role": "negotiator"},
            {"name": "Beta", "role": "negotiator"},
        ],
        success_criteria={"offer": 5},
        max_rounds=4,
    )


def test_seeded_run_does_not_modify_global_random_state() -> None:
    random.seed(123456)
    state_before = random.getstate()

    Simulator(_scenario()).run(seed=42)

    assert random.getstate() == state_before


def test_repeated_runs_on_one_simulator_are_independent() -> None:
    simulator = Simulator(_scenario())

    first = simulator.run(seed=42)
    first_snapshot = copy.deepcopy(first)
    second = simulator.run(seed=42)

    assert first == first_snapshot
    assert second == first
    assert second["history"] is not first["history"]
    assert len(simulator.history) == second["rounds"]


def test_returned_history_cannot_mutate_simulator_state() -> None:
    simulator = Simulator(_scenario())
    result = simulator.run(seed=42)
    internal_snapshot = copy.deepcopy(simulator.history)

    result["history"][0]["Alpha"]["offer"] = 999

    assert simulator.history == internal_snapshot


def test_seeded_legacy_custom_policy_is_repeatable_without_global_rng_drift() -> None:
    simulator = Simulator(_scenario())
    simulator.assign_policy(
        "Alpha",
        lambda _state: {"offer": random.randint(1, 5)},
    )
    random.seed(123456)
    state_before = random.getstate()

    first = simulator.run(seed=42)
    second = simulator.run(seed=42)

    assert second == first
    assert random.getstate() == state_before


def test_custom_policy_can_use_the_run_local_rng() -> None:
    simulator = Simulator(_scenario())
    simulator.assign_policy(
        "Alpha",
        lambda _state, rng: {"offer": rng.randint(1, 5)},
    )

    first = simulator.run(seed=42)
    second = simulator.run(seed=42)

    assert second == first
