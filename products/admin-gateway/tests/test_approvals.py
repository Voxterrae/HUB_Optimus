from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from optimus_admin_gateway.approvals import ApprovalVerifier
from optimus_admin_gateway.config import (
    DEFAULT_APPROVAL_MAX_AGE_SECONDS,
    MAX_APPROVAL_MAX_AGE_SECONDS,
    Settings,
)
from optimus_admin_gateway.models import ApprovalReceipt


SECRET = "synthetic-approval-secret"
PLAN_HASH = "a" * 64
NOW = datetime(2026, 8, 10, 17, 0, tzinfo=timezone.utc)


def signed_receipt(approved_at: datetime = NOW) -> ApprovalReceipt:
    receipt = ApprovalReceipt(
        approval_id="approval-0001",
        plan_hash=PLAN_HASH,
        approved_by="approver@example.com",
        approved_at=approved_at,
        signature="0" * 64,
    )
    material = "|".join(
        [
            receipt.approval_id,
            receipt.plan_hash,
            receipt.approved_by,
            receipt.approved_at.isoformat(),
        ]
    ).encode("utf-8")
    signature = hmac.new(SECRET.encode("utf-8"), material, hashlib.sha256).hexdigest()
    return receipt.model_copy(update={"signature": signature})


def settings_with_max_age(value: object) -> Settings:
    return Settings(
        dev_mode=True,
        catalog_path=Path("unused.json"),
        executor_mode="disabled",
        approval_hmac_secret=None,
        entra_tenant_id=None,
        reader_role="Optimus.Reader",
        mutator_role="Optimus.Mutator",
        approval_max_age_seconds=value,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("age_seconds", [0, DEFAULT_APPROVAL_MAX_AGE_SECONDS])
def test_receipt_is_valid_through_the_inclusive_expiry_boundary(age_seconds: int) -> None:
    verifier = ApprovalVerifier(
        SECRET,
        DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        now=lambda: NOW,
    )
    assert verifier.verify(signed_receipt(NOW - timedelta(seconds=age_seconds)), PLAN_HASH)


def test_receipt_is_invalid_immediately_after_expiry() -> None:
    verifier = ApprovalVerifier(
        SECRET,
        DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        now=lambda: NOW,
    )
    approved_at = NOW - timedelta(seconds=DEFAULT_APPROVAL_MAX_AGE_SECONDS, microseconds=1)
    assert not verifier.verify(signed_receipt(approved_at), PLAN_HASH)


def test_future_receipt_remains_invalid() -> None:
    verifier = ApprovalVerifier(SECRET, DEFAULT_APPROVAL_MAX_AGE_SECONDS, now=lambda: NOW)
    assert not verifier.verify(signed_receipt(NOW + timedelta(microseconds=1)), PLAN_HASH)


def test_wrong_plan_or_signature_remains_invalid() -> None:
    verifier = ApprovalVerifier(SECRET, DEFAULT_APPROVAL_MAX_AGE_SECONDS, now=lambda: NOW)
    receipt = signed_receipt()
    assert not verifier.verify(receipt, "b" * 64)
    assert not verifier.verify(receipt.model_copy(update={"signature": "0" * 64}), PLAN_HASH)


def test_bad_signature_does_not_consult_the_clock() -> None:
    clock_called = False

    def clock() -> datetime:
        nonlocal clock_called
        clock_called = True
        return NOW

    verifier = ApprovalVerifier(SECRET, DEFAULT_APPROVAL_MAX_AGE_SECONDS, now=clock)
    bad_receipt = signed_receipt().model_copy(update={"signature": "0" * 64})
    assert not verifier.verify(bad_receipt, PLAN_HASH)
    assert clock_called is False


def test_unconfigured_secret_and_naive_clock_fail_closed() -> None:
    receipt = signed_receipt()
    assert not ApprovalVerifier(
        None,
        DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        now=lambda: NOW,
    ).verify(receipt, PLAN_HASH)
    naive_now = NOW.replace(tzinfo=None)
    assert not ApprovalVerifier(
        SECRET,
        DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        now=lambda: naive_now,
    ).verify(receipt, PLAN_HASH)


def test_non_utc_receipt_timestamp_is_normalized_to_the_same_instant() -> None:
    local_time = NOW.astimezone(timezone(timedelta(hours=2)))
    receipt = signed_receipt(local_time)
    assert receipt.approved_at == NOW
    verifier = ApprovalVerifier(SECRET, DEFAULT_APPROVAL_MAX_AGE_SECONDS, now=lambda: NOW)
    assert verifier.verify(receipt, PLAN_HASH)


def test_external_signer_vector_uses_the_documented_utc_serialization() -> None:
    receipt = ApprovalReceipt.model_validate(
        {
            "approval_id": "approval-vector-0001",
            "plan_hash": PLAN_HASH,
            "approved_by": "approver@example.com",
            "approved_at": "2026-08-10T19:00:00.123+02:00",
            "signature": "45e112b649725fb084c97cc27fbb9cfdc318f9d368efd5e8cd993947ea86853d",
        }
    )
    verifier = ApprovalVerifier(
        "external-signing-vector-secret",
        DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        now=lambda: datetime(2026, 8, 10, 17, 0, 0, 123000, tzinfo=timezone.utc),
    )
    assert verifier.verify(receipt, PLAN_HASH)


def test_naive_receipt_timestamp_is_rejected_by_the_model() -> None:
    with pytest.raises(ValidationError, match="must include a timezone"):
        ApprovalReceipt(
            approval_id="approval-0001",
            plan_hash=PLAN_HASH,
            approved_by="approver@example.com",
            approved_at=NOW.replace(tzinfo=None),
            signature="0" * 64,
        )


@pytest.mark.parametrize("max_age_seconds", [0, -1, MAX_APPROVAL_MAX_AGE_SECONDS + 1, True, 1.5])
def test_verifier_rejects_out_of_range_or_non_integer_age(max_age_seconds: object) -> None:
    with pytest.raises(ValueError, match="must be an integer from"):
        ApprovalVerifier(SECRET, max_age_seconds=max_age_seconds)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [0, -1, MAX_APPROVAL_MAX_AGE_SECONDS + 1, True, 1.5])
def test_settings_reject_out_of_range_or_non_integer_age(value: object) -> None:
    with pytest.raises(ValueError, match="must be an integer from"):
        settings_with_max_age(value)


def test_settings_use_a_bounded_reference_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPTIMUS_APPROVAL_MAX_AGE_SECONDS", raising=False)
    assert Settings.from_env().approval_max_age_seconds == DEFAULT_APPROVAL_MAX_AGE_SECONDS


def test_settings_accept_a_positive_maximum_age(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTIMUS_APPROVAL_MAX_AGE_SECONDS", "300")
    assert Settings.from_env().approval_max_age_seconds == 300


@pytest.mark.parametrize(
    "value",
    ["", "invalid", "0", "-1", " 900", "+900", "1_000", str(MAX_APPROVAL_MAX_AGE_SECONDS + 1)],
)
def test_settings_reject_invalid_maximum_age(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("OPTIMUS_APPROVAL_MAX_AGE_SECONDS", value)
    with pytest.raises(ValueError, match="must be an integer from"):
        Settings.from_env()
