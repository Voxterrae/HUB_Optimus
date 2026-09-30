from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from .config import MAX_APPROVAL_MAX_AGE_SECONDS, MIN_APPROVAL_MAX_AGE_SECONDS
from .models import (
    APPROVAL_SIGNATURE_PROFILE,
    SHA256_HEX_PATTERN,
    ApprovalReceipt,
)


APPROVAL_SIGNATURE_DOMAIN = b"HUB_OPTIMUS_APPROVAL_RECEIPT\x00"
MIN_APPROVAL_HMAC_SECRET_BYTES = 32
_MAX_LENGTH_PREFIX_VALUE = (1 << 32) - 1


def _length_prefixed_utf8(value: str) -> bytes:
    if type(value) is not str:
        raise ValueError("Approval signature fields must be strings")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Approval signature fields must be valid UTF-8") from exc
    if len(encoded) > _MAX_LENGTH_PREFIX_VALUE:
        raise ValueError("Approval signature field exceeds the v1 length limit")
    return len(encoded).to_bytes(4, "big", signed=False) + encoded


def approval_signature_material(receipt: ApprovalReceipt) -> bytes:
    """Return the domain-separated, length-prefixed v1 signing material."""
    if receipt.signature_profile != APPROVAL_SIGNATURE_PROFILE:
        raise ValueError("Unsupported approval signature profile")
    approved_at = receipt.approved_at
    if not isinstance(approved_at, datetime):
        raise ValueError("Approval timestamp must be a datetime")
    if approved_at.tzinfo is None or approved_at.utcoffset() is None:
        raise ValueError("Approval timestamp must include a timezone")
    fields = (
        receipt.signature_profile,
        receipt.approval_id,
        receipt.plan_hash,
        receipt.approved_by,
        approved_at.astimezone(timezone.utc).isoformat(),
    )
    return APPROVAL_SIGNATURE_DOMAIN + b"".join(
        _length_prefixed_utf8(field) for field in fields
    )


class ApprovalVerifier:
    def __init__(
        self,
        secret: str | None,
        max_age_seconds: int,
        now: Callable[[], datetime] | None = None,
    ):
        if type(max_age_seconds) is not int or not (
            MIN_APPROVAL_MAX_AGE_SECONDS <= max_age_seconds <= MAX_APPROVAL_MAX_AGE_SECONDS
        ):
            raise ValueError(
                f"Approval maximum age must be an integer from "
                f"{MIN_APPROVAL_MAX_AGE_SECONDS} to {MAX_APPROVAL_MAX_AGE_SECONDS} seconds"
            )
        if secret is None or secret == "":
            self._secret = None
        else:
            if type(secret) is not str:
                raise ValueError("Approval HMAC secret must be a string")
            try:
                self._secret = secret.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError("Approval HMAC secret must be valid UTF-8") from exc
            if len(self._secret) < MIN_APPROVAL_HMAC_SECRET_BYTES or secret.isspace():
                raise ValueError(
                    "Approval HMAC secret must contain at least 32 UTF-8 bytes "
                    "and not be whitespace-only"
                )
        self._max_age = timedelta(seconds=max_age_seconds)
        self._now = now or (lambda: datetime.now(timezone.utc))

    @property
    def configured(self) -> bool:
        return self._secret is not None

    def verify(self, receipt: ApprovalReceipt, expected_plan_hash: str) -> bool:
        if self._secret is None:
            return False
        try:
            signature_profile = receipt.signature_profile
            signature = receipt.signature
        except AttributeError:
            return False
        if (
            type(signature_profile) is not str
            or signature_profile != APPROVAL_SIGNATURE_PROFILE
            or type(signature) is not str
        ):
            return False
        if re.fullmatch(SHA256_HEX_PATTERN, signature) is None:
            return False
        try:
            material = approval_signature_material(receipt)
        except (AttributeError, OverflowError, TypeError, ValueError):
            return False
        expected = hmac.new(self._secret, material, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return False
        if receipt.plan_hash != expected_plan_hash:
            return False
        current_time = self._now()
        if current_time.tzinfo is None or current_time.utcoffset() is None:
            return False
        age = current_time.astimezone(timezone.utc) - receipt.approved_at
        return timedelta(0) <= age <= self._max_age
