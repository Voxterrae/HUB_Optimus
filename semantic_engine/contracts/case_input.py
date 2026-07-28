"""Versioned input validation for the HUB_Optimus Semantic Engine."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

CASE_INPUT_SCHEMA_PATH = Path(__file__).with_name("case_input.schema.json")


class CaseInputValidationError(ValueError):
    """A controlled CaseInput contract or referential-integrity error."""


@lru_cache(maxsize=1)
def load_case_input_schema() -> dict[str, Any]:
    """Load and validate the versioned CaseInput JSON Schema."""

    schema = json.loads(CASE_INPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


@lru_cache(maxsize=1)
def _case_input_validator() -> Draft202012Validator:
    return Draft202012Validator(load_case_input_schema())


def _json_path(parts: Iterable[str | int]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part):
            path += f".{part}"
        else:
            path += f"[{json.dumps(part, ensure_ascii=False)}]"
    return path


def _schema_error_path(error: ValidationError) -> str:
    parts = list(error.absolute_path)

    if error.validator == "required":
        missing = sorted(set(error.validator_value) - set(error.instance))
        if missing:
            parts.append(missing[0])

    if error.validator == "additionalProperties":
        allowed = set(error.schema.get("properties", {}))
        unknown = sorted(set(error.instance) - allowed)
        if unknown:
            parts.append(unknown[0])

    return _json_path(parts)


def _schema_error_message(error: ValidationError) -> str:
    if error.validator == "required":
        field_name = _schema_error_path(error).rsplit(".", 1)[-1]
        return f"missing required string field: {field_name}"
    if error.validator == "additionalProperties":
        return "unknown field"
    return error.message


def _schema_error_sort_key(error: ValidationError) -> tuple[str, str]:
    return (_schema_error_path(error), _schema_error_message(error))


def _validate_schema(payload: dict[str, Any]) -> None:
    errors = sorted(_case_input_validator().iter_errors(payload), key=_schema_error_sort_key)
    if not errors:
        return

    error = errors[0]
    if error.validator == "required":
        raise CaseInputValidationError(
            f"{_schema_error_message(error)} at {_schema_error_path(error)}"
        )
    raise CaseInputValidationError(
        f"{_schema_error_path(error)}: {_schema_error_message(error)}"
    )


def _validate_unique_record_ids(payload: dict[str, Any]) -> None:
    for collection_name, id_field in (
        ("claims", "claim_id"),
        ("evidence", "evidence_id"),
    ):
        first_seen: dict[str, int] = {}
        for index, record in enumerate(payload.get(collection_name, [])):
            record_id = record[id_field]
            if record_id in first_seen:
                first_path = f"$.{collection_name}[{first_seen[record_id]}].{id_field}"
                raise CaseInputValidationError(
                    f"$.{collection_name}[{index}].{id_field}: "
                    f"duplicate {id_field} {record_id!r}; first declared at {first_path}"
                )
            first_seen[record_id] = index


def _validate_evidence_references(payload: dict[str, Any]) -> None:
    claim_ids = {claim["claim_id"] for claim in payload.get("claims", [])}

    for evidence_index, evidence in enumerate(payload.get("evidence", [])):
        for field_name in ("supports_claim_ids", "contradicts_claim_ids"):
            for reference_index, claim_id in enumerate(evidence.get(field_name, [])):
                if claim_id not in claim_ids:
                    raise CaseInputValidationError(
                        f"$.evidence[{evidence_index}].{field_name}[{reference_index}]: "
                        f"unknown claim_id {claim_id!r}"
                    )


def validate_case_input(payload: dict[str, Any]) -> None:
    """Validate one CaseInput v1 object and its cross-record integrity."""

    _validate_schema(payload)
    _validate_unique_record_ids(payload)
    _validate_evidence_references(payload)
