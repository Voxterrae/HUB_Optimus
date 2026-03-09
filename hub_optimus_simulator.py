"""
Simulation kernel for HUB_Optimus.

This module defines the core classes used to run negotiation scenarios in HUB_Optimus.  It is intentionally
minimal and focuses on loading scenarios, assigning policies to actors, running negotiation rounds and
detecting success conditions.  The kernel is extensible via policy functions and could be enhanced with
more sophisticated negotiation strategies or external libraries (e.g. NegMAS) without altering these core
definitions.
"""

from __future__ import annotations

import json
import random
from typing import Any, Callable, Dict, List, Optional


# ── Negotiation policies ────────────────────────────────────


class NegotiationPolicy:
    """Base class for negotiation policies."""

    name: str = "base"

    def propose(self, actor_role: str, state: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
        raise NotImplementedError


class UniformRandomPolicy(NegotiationPolicy):
    """Original default: uniform random offer in [1, 5]."""

    name = "uniform"

    def propose(self, actor_role: str, state: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
        return {"offer": rng.randint(1, 5)}


class BiasedRandomPolicy(NegotiationPolicy):
    """Role-aware policy: offer range depends on actor role.

    - hardliner: biased toward high offers (3–5)
    - mediator:  biased toward middle offers (2–4)
    - all others (negotiator, etc.): uniform [1, 5]
    """

    name = "biased"

    def propose(self, actor_role: str, state: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
        if actor_role == "hardliner":
            return {"offer": rng.randint(3, 5)}
        if actor_role == "mediator":
            return {"offer": rng.randint(2, 4)}
        return {"offer": rng.randint(1, 5)}


POLICIES: Dict[str, NegotiationPolicy] = {
    "uniform": UniformRandomPolicy(),
    "biased": BiasedRandomPolicy(),
}


def get_policy(name: str) -> NegotiationPolicy:
    """Look up a policy by name."""
    if name not in POLICIES:
        raise ValueError(f"Unknown policy: {name!r}. Available: {sorted(POLICIES)}")
    return POLICIES[name]


class Scenario:
    """Data container for a negotiation scenario.

    A scenario describes the context, participating actors and the success criteria for a negotiation.
    It can be loaded from a JSON or YAML file (YAML support requires pyyaml).
    """

    def __init__(
        self,
        title: str,
        description: str,
        roles: List[Dict[str, str]],
        success_criteria: Dict[str, Any],
        max_rounds: int = 5,
    ) -> None:
        self.title = title
        self.description = description
        self.roles = roles
        self.success_criteria = success_criteria
        self.max_rounds = max_rounds

    @classmethod
    def from_json(cls, filepath: str) -> "Scenario":
        """Load a scenario from a JSON file.

        Args:
            filepath: Path to the scenario JSON file.

        Returns:
            A Scenario instance populated from the JSON data.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            title=data.get("title", "Unnamed scenario"),
            description=data.get("description", ""),
            roles=data.get("roles", []),
            success_criteria=data.get("success_criteria", {}),
            max_rounds=data.get("max_rounds", 5),
        )


class Actor:
    """Represents a participating party in a scenario.

    Each actor has a name, a role type and a policy function that determines its actions at each round.
    If no policy is provided, a default random offering policy is used.
    """

    def __init__(
        self,
        name: str,
        role_type: str,
        policy: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> None:
        self.name = name
        self.role_type = role_type
        self.policy = policy or self.default_policy
        self._negotiation_policy: Optional[NegotiationPolicy] = None

    def default_policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Default policy for actors.

        Produces a random integer offer between 1 and 5.  Real implementations should assign more
        meaningful policies depending on the actor role and the scenario context.
        """
        return {"offer": random.randint(1, 5)}

    def act(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Return an action for the given negotiation state by calling the actor's policy."""
        if self._negotiation_policy is not None:
            rng = random.Random(random.random())
            return self._negotiation_policy.propose(self.role_type, state, rng)
        return self.policy(state)


class Simulator:
    """Runs negotiation scenarios and records history and outcomes.

    This class orchestrates the interaction between multiple actors across multiple rounds until either the
    success criteria are met or the maximum number of rounds is reached.  It can be extended to support
    more complex negotiation logic, richer histories and evaluation metrics.
    """

    def __init__(self, scenario: Scenario, policy_name: Optional[str] = None) -> None:
        self.scenario = scenario
        # Instantiate actors based on scenario roles
        self.actors: List[Actor] = [Actor(role["name"], role.get("role", "")) for role in scenario.roles]
        self.history: List[Dict[str, Dict[str, Any]]] = []
        if policy_name is not None:
            neg_policy = get_policy(policy_name)
            for actor in self.actors:
                actor._negotiation_policy = neg_policy

    def assign_policy(
        self, actor_name: str, policy: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """Assign a custom policy to an actor by name."""
        for actor in self.actors:
            if actor.name == actor_name:
                actor.policy = policy
                break

    def check_success(self, actions: Dict[str, Dict[str, Any]]) -> bool:
        """Check if the success criteria are satisfied by the actions of this round."""
        for key, expected_value in self.scenario.success_criteria.items():
            for actor_action in actions.values():
                if actor_action.get(key) == expected_value:
                    return True
        return False

    def run(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """Execute the negotiation scenario.

        Args:
            seed: An optional integer seed for reproducibility.  If provided, random actions will be
                reproducible across runs.

        Returns:
            A dictionary with the status ("success" or "failure"), the number of rounds executed,
            the history of actions and a detail message.
        """
        rng = random.Random(seed)
        status: str = "failure"
        for round_number in range(1, self.scenario.max_rounds + 1):
            actions: Dict[str, Dict[str, Any]] = {}
            for actor in self.actors:
                # Use a deterministic seed to reproduce each actor's random choices
                random.seed(rng.random())
                actions[actor.name] = actor.act(
                    {
                        "round": round_number,
                        "history": self.history,
                        "actors": [a.name for a in self.actors],
                    }
                )
            self.history.append(actions)
            if self.check_success(actions):
                status = "success"
                return {
                    "status": status,
                    "rounds": round_number,
                    "history": self.history,
                    "detail": f"Success criteria met at round {round_number}",
                }
        return {
            "status": status,
            "rounds": self.scenario.max_rounds,
            "history": self.history,
            "detail": "Max rounds reached without meeting success criteria",
        }