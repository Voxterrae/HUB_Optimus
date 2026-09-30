from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAILBOX_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SAFE_ID_PATTERN_TEXT = r"^[A-Za-z0-9._-]{1,128}$"
SAFE_KEY_PATTERN_TEXT = r"^[A-Za-z0-9._-]{8,128}$"
SAFE_ID_PATTERN = re.compile(SAFE_ID_PATTERN_TEXT)
SHA256_HEX_PATTERN = r"^[a-f0-9]{64}$"
APPROVAL_SIGNATURE_PROFILE = "hmac-sha256-lp-v1"
APPROVAL_TIMESTAMP_INPUT_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class JobState(StrEnum):
    planned = "PLANNED"
    approval_required = "APPROVAL_REQUIRED"
    queued = "QUEUED"
    running = "RUNNING"
    succeeded = "SUCCEEDED"
    failed = "FAILED"
    cancelled = "CANCELLED"


class Principal(StrictModel):
    subject_id: str = Field(min_length=1, max_length=128)
    display_name: str | None = Field(default=None, max_length=256)
    roles: set[str] = Field(default_factory=set)


class OperationDefinition(StrictModel):
    operation_id: str
    title: str
    category: Literal["exchange", "powershell"]
    mutation: bool
    approval_required: bool
    risk: RiskLevel
    executor: str
    parameter_schema: str
    description: str

    @field_validator("operation_id", "executor", "parameter_schema")
    @classmethod
    def validate_safe_id(cls, value: str) -> str:
        if not SAFE_ID_PATTERN.fullmatch(value):
            raise ValueError("must be an allowlisted identifier")
        return value

    @model_validator(mode="after")
    def mutation_requires_approval(self) -> "OperationDefinition":
        if self.mutation and not self.approval_required:
            raise ValueError("mutation operations must require approval")
        return self


class MailboxTarget(StrictModel):
    mailbox: str = Field(min_length=3, max_length=320)

    @field_validator("mailbox")
    @classmethod
    def validate_mailbox(cls, value: str) -> str:
        if not MAILBOX_PATTERN.fullmatch(value):
            raise ValueError("must be a mailbox SMTP address")
        return value.lower()


class MailboxAndDelegate(MailboxTarget):
    delegate: str = Field(min_length=3, max_length=320)

    @field_validator("delegate")
    @classmethod
    def validate_delegate(cls, value: str) -> str:
        if not MAILBOX_PATTERN.fullmatch(value):
            raise ValueError("must be a delegate SMTP address")
        return value.lower()


class FullAccessChange(MailboxAndDelegate):
    automapping: bool = False
    reason: str = Field(min_length=8, max_length=500)
    change_ticket: str = Field(min_length=3, max_length=128)


class JobTarget(StrictModel):
    job_id: str = Field(min_length=8, max_length=128, pattern=SAFE_KEY_PATTERN_TEXT)


PARAMETER_MODELS: dict[str, type[StrictModel]] = {
    "MailboxTarget": MailboxTarget,
    "MailboxAndDelegate": MailboxAndDelegate,
    "FullAccessChange": FullAccessChange,
    "JobTarget": JobTarget,
}


class ApprovalReceipt(StrictModel):
    signature_profile: Literal[APPROVAL_SIGNATURE_PROFILE]
    approval_id: str = Field(min_length=8, max_length=128, pattern=SAFE_KEY_PATTERN_TEXT)
    plan_hash: str = Field(min_length=64, max_length=64, pattern=SHA256_HEX_PATTERN)
    approved_by: str = Field(min_length=1, max_length=256)
    approved_at: datetime
    signature: str = Field(min_length=64, max_length=64, pattern=SHA256_HEX_PATTERN)

    @field_validator("signature_profile", "signature", mode="before")
    @classmethod
    def exact_security_string(cls, value: object) -> object:
        if type(value) is not str or value != value.strip():
            raise ValueError("must be an exact non-whitespace-padded string")
        return value

    @field_validator("approved_at", mode="before")
    @classmethod
    def strict_timestamp_input(cls, value: object) -> object:
        if isinstance(value, datetime):
            return value
        if type(value) is not str or APPROVAL_TIMESTAMP_INPUT_PATTERN.fullmatch(value) is None:
            raise ValueError("approved_at must be an RFC3339 date-time string")
        return value

    @field_validator("approved_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("approved_at must include a timezone")
        try:
            if value.utcoffset() is None:
                raise ValueError("approved_at must include a timezone")
            return value.astimezone(timezone.utc)
        except (OverflowError, ValueError) as exc:
            raise ValueError("approved_at must be representable in UTC") from exc


class OperationRequest(StrictModel):
    parameters: dict[str, Any]
    dry_run: bool = True
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=SAFE_KEY_PATTERN_TEXT)
    approval: ApprovalReceipt | None = None


class OperationPlan(StrictModel):
    operation_id: str
    title: str
    mutation: bool
    approval_required: bool
    risk: RiskLevel
    dry_run: bool
    parameters: dict[str, Any]
    plan_hash: str
    catalog_version: str
    state: JobState


class ExecutionResult(StrictModel):
    job_id: str
    operation_id: str
    state: JobState
    dry_run: bool
    plan_hash: str
    message: str
    output: dict[str, Any] = Field(default_factory=dict)


def canonical_plan_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
