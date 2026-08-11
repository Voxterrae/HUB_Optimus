from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from .config import MAX_APPROVAL_MAX_AGE_SECONDS, MIN_APPROVAL_MAX_AGE_SECONDS
from .models import ApprovalReceipt


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
        self._secret = secret.encode("utf-8") if secret else None
        self._max_age = timedelta(seconds=max_age_seconds)
        self._now = now or (lambda: datetime.now(timezone.utc))

    @property
    def configured(self) -> bool:
        return self._secret is not None

    def verify(self, receipt: ApprovalReceipt, expected_plan_hash: str) -> bool:
        if self._secret is None:
            return False
        material = "|".join(
            [receipt.approval_id, receipt.plan_hash, receipt.approved_by, receipt.approved_at.isoformat()]
        ).encode("utf-8")
        expected = hmac.new(self._secret, material, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, receipt.signature):
            return False
        if receipt.plan_hash != expected_plan_hash:
            return False
        current_time = self._now()
        if current_time.tzinfo is None or current_time.utcoffset() is None:
            return False
        age = current_time.astimezone(timezone.utc) - receipt.approved_at
        return timedelta(0) <= age <= self._max_age
