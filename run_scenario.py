"""
Command-line utility to run negotiation scenarios with fail-fast input validation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from hub_optimus_simulator import Scenario, Simulator


INPUT_ERROR_EXIT_CODE = 2
RUNTIME_ERROR_EXIT_CODE = 1
SCHEMA_PATH = Path(__file__).with_name("scenario.schema.json")


class ScenarioValidationError(ValueError):
    """Raised when a scenario input is invalid against the schema contract."""


def _format_error_path(error: ValidationError) -> str:
    if not error.absolute_path:
        return "$"

    path = "$"
    for part in error.absolute_path:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def _load_schema_validator(schema_path: Path = SCHEMA_PATH) -> Draft202012Validator:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Schema file not found: {schema_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid schema JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate_payload_with_schema(payload: Any) -> list[str]:
    validator = _load_schema_validator()
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda err: (list(err.absolute_path), err.message),
    )
    return [f"{_format_error_path(error)}: {error.message}" for error in errors]


def load_validated_scenario(scenario_path: Path) -> Scenario:
    try:
        payload: Any = json.loads(scenario_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioValidationError(
            f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    errors = _validate_payload_with_schema(payload)
    if errors:
        raise ScenarioValidationError(
            "Scenario does not match scenario.schema.json:\n" + "\n".join(errors)
        )

    if not isinstance(payload, dict):
        raise ScenarioValidationError("Scenario root must be a JSON object")

    return Scenario(
        title=str(payload["title"]),
        description=str(payload["description"]),
        roles=list(payload["roles"]),
        success_criteria=dict(payload["success_criteria"]),
        max_rounds=int(payload["max_rounds"]),
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
        simulator = Simulator(scenario)
        result = simulator.run(seed=args.seed)
    except ScenarioValidationError as exc:
        print(f"[schema-error] {exc}", file=sys.stderr)
        return INPUT_ERROR_EXIT_CODE
    except Exception as exc:  # pragma: no cover - defensive runtime boundary
        print(f"[runtime-error] {exc}", file=sys.stderr)
        return RUNTIME_ERROR_EXIT_CODE

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
