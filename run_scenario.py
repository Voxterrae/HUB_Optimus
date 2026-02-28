"""
Command-line utility to run negotiation scenarios with fail-fast input validation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema

from hub_optimus_simulator import Scenario, Simulator


SCHEMA_PATH = Path(__file__).parent / "scenario.schema.json"
INPUT_ERROR_EXIT_CODE = 2


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_scenario_payload(payload: object) -> list[str]:
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    return [
        f"{'.'.join(str(p) for p in e.path)}: {e.message}" if e.path else e.message
        for e in errors
    ]


def load_validated_scenario(scenario_path: Path) -> Scenario:
    try:
        payload: Any = json.loads(scenario_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    errors = validate_scenario_payload(payload)
    if errors:
        raise ValueError("\n".join(errors))

    assert isinstance(payload, dict)
    assert isinstance(payload["title"], str)
    assert isinstance(payload["description"], str)
    assert isinstance(payload["roles"], list)
    assert isinstance(payload["success_criteria"], dict)
    assert isinstance(payload["max_rounds"], int)

    return Scenario(
        title=payload["title"],
        description=payload["description"],
        roles=payload["roles"],
        success_criteria=payload["success_criteria"],
        max_rounds=payload["max_rounds"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a HUB_Optimus negotiation scenario and output JSON results."
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
            "Optional seed for reproducibility. If provided, random actions will be deterministic,"
            " enabling reproducible runs."
        ),
    )
    args = parser.parse_args()

    scenario_path = Path(args.scenario)
    if not scenario_path.is_file():
        print(f"[input-error] Scenario file not found: {scenario_path}", file=sys.stderr)
        return INPUT_ERROR_EXIT_CODE

    try:
        scenario = load_validated_scenario(scenario_path)
    except ValueError as exc:
        print(f"[schema-error] {exc}", file=sys.stderr)
        return INPUT_ERROR_EXIT_CODE

    simulator = Simulator(scenario)
    result = simulator.run(seed=args.seed)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
