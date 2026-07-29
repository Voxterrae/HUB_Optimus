"""
Authoritative scenario loader and CLI with fail-fast input validation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

import jsonschema

from hub_optimus_simulator import POLICIES, Scenario, Simulator


SCHEMA_PATH = Path(__file__).parent / "scenario.schema.json"
INPUT_ERROR_EXIT_CODE = 2


class ScenarioInputError(Exception):
    """A controlled failure while reading the user-supplied scenario file."""


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _reject_non_standard_json_constant(value: str) -> NoReturn:
    raise ValueError(f"non-standard JSON constant {value!r} is not permitted")


def _actor_identity_errors(payload: object) -> list[str]:
    """Return cross-record actor identity errors after structural validation."""
    if not isinstance(payload, dict):
        return []
    roles = payload.get("roles")
    if not isinstance(roles, list):
        return []

    errors: list[str] = []
    first_index_by_name: dict[str, int] = {}
    for index, role in enumerate(roles):
        if not isinstance(role, dict):
            continue
        name = role.get("name")
        if not isinstance(name, str):
            continue
        if name in first_index_by_name:
            errors.append(
                f"roles.{index}.name: duplicate actor name {name!r}; "
                f"first declared at roles.{first_index_by_name[name]}.name"
            )
        else:
            first_index_by_name[name] = index
    return errors


def validate_scenario_payload(payload: object) -> list[str]:
    """Return structural schema and cross-record identity errors."""
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    messages = [
        f"{'.'.join(str(p) for p in e.path)}: {e.message}" if e.path else e.message
        for e in errors
    ]
    messages.extend(_actor_identity_errors(payload))
    return messages


def load_validated_scenario(scenario_path: Path) -> Scenario:
    try:
        source = scenario_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ScenarioInputError(f"cannot read scenario file: {exc}") from exc

    try:
        payload: Any = json.loads(
            source,
            parse_constant=_reject_non_standard_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except ValueError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

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
        "scenario_path_pos",
        nargs="?",
        help="Path to the scenario definition file in JSON format (positional).",
    )
    parser.add_argument(
        "--scenario",
        dest="scenario_path_opt",
        required=False,
        help="Path to the scenario definition file in JSON format.",
    )
    parser.add_argument(
        "--output",
        help=(
            "Optional path to write the JSON results. Defaults to the scenario path "
            "with a .result.json suffix."
        ),
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
    parser.add_argument(
        "--policy",
        choices=sorted(POLICIES),
        default=None,
        help="Negotiation policy for all actors (default: uniform random).",
    )
    args = parser.parse_args()

    scenario_path_value = args.scenario_path_opt or args.scenario_path_pos
    if not scenario_path_value:
        parser.print_usage(sys.stderr)
        print("[input-error] Scenario path is required.", file=sys.stderr)
        return INPUT_ERROR_EXIT_CODE

    scenario_path = Path(scenario_path_value)
    if not scenario_path.is_file():
        print(f"[input-error] Scenario file not found: {scenario_path}", file=sys.stderr)
        return INPUT_ERROR_EXIT_CODE

    try:
        scenario = load_validated_scenario(scenario_path)
    except ScenarioInputError as exc:
        print(f"[input-error] {exc}", file=sys.stderr)
        return INPUT_ERROR_EXIT_CODE
    except ValueError as exc:
        print(f"[schema-error] {exc}", file=sys.stderr)
        return INPUT_ERROR_EXIT_CODE

    simulator = Simulator(scenario, policy_name=args.policy)
    result = simulator.run(seed=args.seed)
    output_path = Path(args.output) if args.output else scenario_path.with_suffix(".result.json")
    try:
        with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(
                json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
                + "\n"
            )
    except OSError as exc:
        print(f"[input-error] cannot write output file: {exc}", file=sys.stderr)
        return INPUT_ERROR_EXIT_CODE
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
