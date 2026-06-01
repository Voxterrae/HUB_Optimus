"""Minimal contract-first CLI for the HUB_Optimus Semantic Engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from semantic_engine.contracts import AnalysisResult

REQUIRED_CASE_FIELDS = ("case_id", "core_version_ref", "input_summary")


class ControlledCliError(Exception):
    """Expected CLI error that should be printed without a traceback."""


def load_case(path: Path) -> dict[str, Any]:
    """Load a case JSON file and return its object payload."""

    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ControlledCliError(f"input file not found: {path}") from exc
    except OSError as exc:
        raise ControlledCliError(f"cannot read input file {path}: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ControlledCliError(f"invalid JSON in {path}: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ControlledCliError("input JSON must be an object")

    return payload


def require_string_field(payload: dict[str, Any], field_name: str) -> str:
    """Return a required non-empty string field or raise a controlled error."""

    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ControlledCliError(f"missing required string field: {field_name}")
    return value


def build_draft_result(payload: dict[str, Any]) -> AnalysisResult:
    """Build a draft AnalysisResult from a minimal case payload."""

    return AnalysisResult(
        case_id=require_string_field(payload, "case_id"),
        core_version_ref=require_string_field(payload, "core_version_ref"),
        input_summary=require_string_field(payload, "input_summary"),
        status="draft",
    )


def analyze_case(input_path: Path) -> dict[str, Any]:
    """Load a minimal case and return the contractual AnalysisResult payload."""

    return build_draft_result(load_case(input_path)).to_dict()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m semantic_engine.cli",
        description="HUB_Optimus Semantic Engine CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze",
        help="Build a draft AnalysisResult from a minimal case JSON file.",
    )
    analyze.add_argument("input", help="Path to a minimal case JSON file.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "analyze":
            payload = analyze_case(Path(args.input))
        else:  # pragma: no cover - argparse prevents this path.
            parser.error(f"unknown command: {args.command}")
    except ControlledCliError as exc:
        print(f"semantic_engine.cli: error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
