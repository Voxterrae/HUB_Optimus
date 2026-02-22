"""
Command-line utility to run negotiation scenarios with fail-fast schema validation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hub_optimus_simulator import Scenario, Simulator

REQUIRED_FIELDS = ("title", "description", "roles", "success_criteria", "max_rounds")


def _validate_role(role: object, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(role, dict):
        return [f"roles[{index}] must be an object"]

    name = role.get("name")
    role_type = role.get("role")

    if not isinstance(name, str) or not name.strip():
        errors.append(f"roles[{index}].name must be a non-empty string")
    if not isinstance(role_type, str) or not role_type.strip():
        errors.append(f"roles[{index}].role must be a non-empty string")

    return errors


def validate_scenario_payload(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["Scenario root must be a JSON object"]

    errors: list[str] = []
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        errors.append(f"Missing required field(s): {', '.join(missing)}")

    unknown = sorted(set(payload.keys()) - set(REQUIRED_FIELDS))
    if unknown:
        errors.append(f"Unknown field(s): {', '.join(unknown)}")

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("title must be a non-empty string")

    description = payload.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append("description must be a non-empty string")

    roles = payload.get("roles")
    if not isinstance(roles, list) or not roles:
        errors.append("roles must be a non-empty list")
    elif isinstance(roles, list):
        for index, role in enumerate(roles):
            errors.extend(_validate_role(role, index))

    success_criteria = payload.get("success_criteria")
    if not isinstance(success_criteria, dict) or not success_criteria:
        errors.append("success_criteria must be a non-empty object")

    max_rounds = payload.get("max_rounds")
    if not isinstance(max_rounds, int) or max_rounds < 1:
        errors.append("max_rounds must be an integer >= 1")

    return errors


def load_validated_scenario(scenario_path: Path) -> Scenario:
    try:
        payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc

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
            "Optional seed for reproducibility. If provided, random actions will be deterministic,"
            " enabling reproducible runs."
        ),
    )
    args = parser.parse_args()

    scenario_path = Path(args.scenario)
    if not scenario_path.is_file():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

    try:
        scenario = load_validated_scenario(scenario_path)
    except ValueError as exc:
        print(f"[schema-error] {exc}", file=sys.stderr)
        raise SystemExit(2)

    simulator = Simulator(scenario)
    result = simulator.run(seed=args.seed)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
