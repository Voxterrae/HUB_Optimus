"""
Command-line utility to run negotiation scenarios with fail-fast input validation.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import jsonschema

from hub_optimus_simulator import Scenario, Simulator


INPUT_ERROR_EXIT_CODE = 2

_SCHEMA_PATH = Path(__file__).resolve().parent / "scenario.schema.json"
_SCHEMA: dict[str, Any] | None = None


def _load_schema() -> dict[str, Any]:
    global _SCHEMA
    if _SCHEMA is None:
        if not _SCHEMA_PATH.is_file():
            raise FileNotFoundError(
                f"Schema file not found: {_SCHEMA_PATH}. "
                "Ensure scenario.schema.json is present in the repository root."
            )
        try:
            _SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in schema file {_SCHEMA_PATH}: {exc}"
            ) from exc
    return _SCHEMA


def _friendly_message(err: jsonschema.ValidationError) -> str:
    path = list(err.absolute_path)
    if path == ["roles"] and err.validator == "minItems":
        return "roles must be a non-empty list"
    if path == ["success_criteria"] and err.validator == "minProperties":
        return "success_criteria must be a non-empty object"
    if path == ["max_rounds"] and err.validator in ("minimum", "type"):
        return "max_rounds must be an integer >= 1"
    if path == ["max_rounds"] and err.validator == "exclusiveMinimum":
        return "max_rounds must be an integer >= 1"
    if len(path) >= 2 and path[0] == "roles" and isinstance(path[1], int):
        idx = path[1]
        field = path[2] if len(path) > 2 else None
        if field:
            return f"roles[{idx}].{field} must be a non-empty string"
        return f"roles[{idx}] {err.message}"
    if not path and err.validator == "additionalProperties":
        m = re.search(r"'([^']+)' was unexpected", err.message)
        extra = m.group(1) if m else err.message
        return f"Unknown field(s): {extra}"
    if not path and err.validator == "required":
        m = re.search(r"'([^']+)' is a required", err.message)
        missing = m.group(1) if m else err.message
        return f"Missing required field(s): {missing}"
    if not path and err.validator == "type":
        return "Scenario root must be a JSON object"
    return err.message


def validate_scenario_payload(payload: object) -> list[str]:
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    raw_errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    return [_friendly_message(e) for e in raw_errors]


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
