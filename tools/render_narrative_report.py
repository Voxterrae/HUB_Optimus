"""
Render a deterministic narrative-risk report from a validated JSON payload.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "datasets" / "ai_risk_narratives" / "narrative_report.schema.json"
ERROR_PREFIX = "[narrative-report:error]"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _format_error(message: str) -> str:
    return f"{ERROR_PREFIX} {message}"


def validate_payload(payload: object) -> list[str]:
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    messages: list[str] = []
    for error in errors:
        prefix = ".".join(str(part) for part in error.path)
        if prefix:
            messages.append(f"{prefix}: {error.message}")
        else:
            messages.append(error.message)
    return messages


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Narrative Risk Report",
        "",
        f"Claim ID: `{payload['claim_id']}`",
        "",
        "## Claim",
        payload["claim"],
        "",
        "## Evidence",
    ]
    for item in payload["evidence"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Inference",
            payload["inference"],
            "",
            "## Mitigation",
        ]
    )
    for item in payload["mitigation"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a narrative-risk report from a JSON payload."
    )
    parser.add_argument("input_path", help="Path to the narrative report JSON payload.")
    parser.add_argument(
        "--output",
        help="Optional path to write the rendered Markdown. Defaults to stdout.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.is_file():
        print(_format_error(f"input file not found: {input_path}"), file=sys.stderr)
        return 1

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(
            _format_error(
                f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
            ),
            file=sys.stderr,
        )
        return 1

    errors = validate_payload(payload)
    if errors:
        print(_format_error("; ".join(errors)), file=sys.stderr)
        return 1

    assert isinstance(payload, dict)
    rendered = render_markdown(payload)

    if args.output:
        with Path(args.output).open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
