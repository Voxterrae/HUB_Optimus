"""Minimal contract-first CLI for the HUB_Optimus Semantic Engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from semantic_engine.contracts import AnalysisResult, ClaimRecord, EvidenceRecord

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


def require_object_item(collection_name: str, index: int, value: Any) -> dict[str, Any]:
    """Return an object item from a collection or raise a controlled error."""

    if not isinstance(value, dict):
        raise ControlledCliError(f"{collection_name}[{index}] must be an object")
    return value


def optional_string_field(
    payload: dict[str, Any],
    field_name: str,
    default: str,
) -> str:
    """Return an optional string field with a stable default."""

    if field_name not in payload:
        return default

    value = payload[field_name]
    if not isinstance(value, str) or not value.strip():
        raise ControlledCliError(f"{field_name} must be a non-empty string")
    return value


def optional_bool_field(
    payload: dict[str, Any],
    field_name: str,
    default: bool,
) -> bool:
    """Return an optional boolean field with a stable default."""

    if field_name not in payload:
        return default

    value = payload[field_name]
    if not isinstance(value, bool):
        raise ControlledCliError(f"{field_name} must be a boolean")
    return value


def optional_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    """Return optional metadata as an object."""

    if "metadata" not in payload:
        return {}

    value = payload["metadata"]
    if not isinstance(value, dict):
        raise ControlledCliError("metadata must be an object")
    return dict(value)


def optional_string_tuple(
    payload: dict[str, Any],
    field_name: str,
) -> tuple[str, ...]:
    """Return an optional list of strings as a tuple."""

    if field_name not in payload:
        return ()

    value = payload[field_name]
    if not isinstance(value, list):
        raise ControlledCliError(f"{field_name} must be a list of strings")

    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ControlledCliError(f"{field_name}[{index}] must be a non-empty string")
        items.append(item)

    return tuple(items)


def load_claims(payload: dict[str, Any]) -> tuple[ClaimRecord, ...]:
    """Load optional structured claims from the case payload."""

    raw_claims = payload.get("claims", [])
    if not isinstance(raw_claims, list):
        raise ControlledCliError("claims must be a list")

    claims: list[ClaimRecord] = []
    for index, raw_claim in enumerate(raw_claims):
        claim = require_object_item("claims", index, raw_claim)
        claims.append(
            ClaimRecord(
                claim_id=require_string_field(claim, "claim_id"),
                text=require_string_field(claim, "text"),
                source_ref=require_string_field(claim, "source_ref"),
                claim_type=optional_string_field(claim, "claim_type", "unknown"),
                requires_evidence=optional_bool_field(
                    claim,
                    "requires_evidence",
                    True,
                ),
                status=optional_string_field(claim, "status", "pending"),
                metadata=optional_metadata(claim),
            )
        )

    return tuple(claims)


def load_evidence(payload: dict[str, Any]) -> tuple[EvidenceRecord, ...]:
    """Load optional structured evidence from the case payload."""

    raw_evidence = payload.get("evidence", [])
    if not isinstance(raw_evidence, list):
        raise ControlledCliError("evidence must be a list")

    evidence: list[EvidenceRecord] = []
    for index, raw_item in enumerate(raw_evidence):
        item = require_object_item("evidence", index, raw_item)
        evidence.append(
            EvidenceRecord(
                evidence_id=require_string_field(item, "evidence_id"),
                text=require_string_field(item, "text"),
                source_ref=require_string_field(item, "source_ref"),
                source_type=optional_string_field(item, "source_type", "unknown"),
                supports_claim_ids=optional_string_tuple(item, "supports_claim_ids"),
                contradicts_claim_ids=optional_string_tuple(
                    item,
                    "contradicts_claim_ids",
                ),
                limitations=optional_string_tuple(item, "limitations"),
                metadata=optional_metadata(item),
            )
        )

    return tuple(evidence)


def build_draft_result(payload: dict[str, Any]) -> AnalysisResult:
    """Build a draft AnalysisResult from a structured case payload.

    This preserves submitted claims, evidence, process notes, and operational
    signal fields without adding scoring, model-judge behavior, or autonomous
    conclusions.
    """

    return AnalysisResult(
        case_id=require_string_field(payload, "case_id"),
        core_version_ref=require_string_field(payload, "core_version_ref"),
        input_summary=require_string_field(payload, "input_summary"),
        claims=load_claims(payload),
        evidence=load_evidence(payload),
        inferences=optional_string_tuple(payload, "inferences"),
        uncertainties=optional_string_tuple(payload, "uncertainties"),
        narrative_amplification=optional_string_tuple(
            payload,
            "narrative_amplification",
        ),
        operational_signal=optional_string_field(
            payload,
            "operational_signal",
            "none",
        ),
        status=optional_string_field(payload, "status", "draft"),
        metadata=optional_metadata(payload),
    )


def analyze_case(input_path: Path) -> dict[str, Any]:
    """Load a minimal case and return the contractual AnalysisResult payload."""

    return build_draft_result(load_case(input_path)).to_dict()


def serialize_payload(payload: dict[str, Any]) -> str:
    """Return stable JSON for CLI stdout or file output."""

    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_output(path: Path, content: str) -> None:
    """Write CLI output to a UTF-8 file, creating parent directories."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ControlledCliError(f"cannot write output file {path}: {exc}") from exc


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
    analyze.add_argument(
        "--output",
        help="Optional path for writing the contractual JSON result instead of stdout.",
    )

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

    content = serialize_payload(payload)

    if args.output:
        try:
            write_output(Path(args.output), content)
        except ControlledCliError as exc:
            print(f"semantic_engine.cli: error: {exc}", file=sys.stderr)
            return 1
    else:
        print(content, end="")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
