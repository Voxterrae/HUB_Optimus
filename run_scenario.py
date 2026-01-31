"""
Command-line utility to run negotiation scenarios using the HUB_Optimus simulation kernel.

This script loads a scenario from a JSON file, instantiates a simulator and executes the negotiation
rounds.  The output is printed as pretty‑formatted JSON, including the status, the number of rounds
executed, the complete history of actions and a descriptive detail message.
"""

import argparse
import json
from pathlib import Path

from hub_optimus_simulator import Scenario, Simulator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a HUB_Optimus negotiation scenario and output the results as JSON."
    )
    parser.add_argument(
        "--scenario",
        required=True,
        help="Path to the scenario definition file in JSON format.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=(
            "Optional seed for reproducibility.  If provided, random actions will be deterministic,"
            " enabling reproducible runs."
        ),
    )
    args = parser.parse_args()

    scenario_path = Path(args.scenario)
    if not scenario_path.is_file():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")
    scenario = Scenario.from_json(str(scenario_path))
    simulator = Simulator(scenario)
    result = simulator.run(seed=args.seed)
    # Pretty print the result as UTF‑8 encoded JSON
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()