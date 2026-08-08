from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone

from .models import ApprovalReceipt


class ApprovalVerifier:
    def __init__(self, secret: str | None):
        self._secret = secret.encode("utf-8") if secret else None

    @property
    def configured(self) -> bool:
        return self._secret is not None

    def verify(self, receipt: ApprovalReceipt, expected_plan_hash: str) -> bool:
        if self._secret is None or receipt.plan_hash != expected_plan_hash:
            return False
        if receipt.approved_at > datetime.now(timezone.utc):
            return False
        material = "|".join(
            [receipt.approval_id, receipt.plan_hash, receipt.approved_by, receipt.approved_at.isoformat()]
        ).encode("utf-8")
        expected = hmac.new(self._secret, material, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, receipt.signature)
