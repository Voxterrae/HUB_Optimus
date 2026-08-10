from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from optimus_admin_gateway.approvals import (
    APPROVAL_SIGNATURE_DOMAIN,
    ApprovalVerifier,
    approval_signature_material,
)
from optimus_admin_gateway.config import (
    DEFAULT_APPROVAL_MAX_AGE_SECONDS,
    MAX_APPROVAL_MAX_AGE_SECONDS,
    Settings,
)
from optimus_admin_gateway.models import APPROVAL_SIGNATURE_PROFILE, ApprovalReceipt


SECRET = "synthetic-approval-secret-32-bytes"
PLAN_HASH = "a" * 64
NOW = datetime(2026, 8, 10, 17, 0, tzinfo=timezone.utc)
EXTERNAL_VECTOR_SECRET = "external-signing-vector-secret-32"
EXTERNAL_VECTOR_SIGNATURE = "c6196583fde6c8d51e2c9f1539eecc9dc52e45d67067886b4a4a3962f2199598"
EXTERNAL_VECTOR_MATERIAL_HEX = (
    "4855425f4f5054494d55535f415050524f56414c5f5245434549505400"
    "00000011686d61632d7368613235362d6c702d7631"
    "00000014617070726f76616c2d766563746f722d30303031"
    "0000004061616161616161616161616161616161616161616161616161616161"
    "6161616161616161616161616161616161616161616161616161616161616161"
    "61616161"
    "00000014617070726f766572406578616d706c652e636f6d"
    "00000020323032362d30382d31305431373a30303a30302e3132333030302b30303a3030"
)
UNICODE_VECTOR_SIGNATURE = "52a61cc8461620d8ca86891c7009cc9226c03bc75d1583c6fa4fe09bdeafe5d1"
UNICODE_VECTOR_MATERIAL_HEX = (
    "4855425f4f5054494d55535f415050524f56414c5f5245434549505400"
    "00000011686d61632d7368613235362d6c702d7631"
    "00000019617070726f76616c2d766563746f722d757466382d30303031"
    "0000004062626262626262626262626262626262626262626262626262626262"
    "6262626262626262626262626262626262626262626262626262626262626262"
    "62626262"
    "00000015617070726f7576c3a9406578616d706c652e636f6d"
    "00000019323032362d30382d31305431373a30303a30302b30303a3030"
)


def signed_receipt(
    approved_at: datetime = NOW,
    *,
    approval_id: str = "approval-0001",
    plan_hash: str = PLAN_HASH,
    approved_by: str = "approver@example.com",
) -> ApprovalReceipt:
    receipt = ApprovalReceipt(
        signature_profile=APPROVAL_SIGNATURE_PROFILE,
        approval_id=approval_id,
        plan_hash=plan_hash,
        approved_by=approved_by,
        approved_at=approved_at,
        signature="0" * 64,
    )
    material = approval_signature_material(receipt)
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
            "signature_profile": "hmac-sha256-lp-v1",
            "approval_id": "approval-vector-0001",
            "plan_hash": PLAN_HASH,
            "approved_by": "approver@example.com",
            "approved_at": "2026-08-10T19:00:00.123+02:00",
            "signature": EXTERNAL_VECTOR_SIGNATURE,
        }
    )
    assert approval_signature_material(receipt).hex() == EXTERNAL_VECTOR_MATERIAL_HEX
    verifier = ApprovalVerifier(
        EXTERNAL_VECTOR_SECRET,
        DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        now=lambda: datetime(2026, 8, 10, 17, 0, 0, 123000, tzinfo=timezone.utc),
    )
    assert verifier.verify(receipt, PLAN_HASH)


def test_security_document_publishes_the_exact_external_vector() -> None:
    security = (Path(__file__).parents[1] / "docs" / "SECURITY.md").read_text(encoding="utf-8")
    assert f"secret: {EXTERNAL_VECTOR_SECRET}" in security
    assert f"material hex: {EXTERNAL_VECTOR_MATERIAL_HEX}" in security
    assert f"HMAC: {EXTERNAL_VECTOR_SIGNATURE}" in security
    assert f"material hex: {UNICODE_VECTOR_MATERIAL_HEX}" in security
    assert f"HMAC: {UNICODE_VECTOR_SIGNATURE}" in security


def test_external_unicode_vector_uses_utf8_byte_lengths() -> None:
    receipt = ApprovalReceipt.model_validate(
        {
            "signature_profile": APPROVAL_SIGNATURE_PROFILE,
            "approval_id": "approval-vector-utf8-0001",
            "plan_hash": "b" * 64,
            "approved_by": "approuvé@example.com",
            "approved_at": "2026-08-10T17:00:00Z",
            "signature": UNICODE_VECTOR_SIGNATURE,
        }
    )
    assert approval_signature_material(receipt).hex() == UNICODE_VECTOR_MATERIAL_HEX
    verifier = ApprovalVerifier(
        EXTERNAL_VECTOR_SECRET,
        DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        now=lambda: NOW,
    )
    assert verifier.verify(receipt, "b" * 64)


def test_pydantic_schema_exposes_the_exact_signature_profile() -> None:
    schema = ApprovalReceipt.model_json_schema()
    assert schema["required"] == [
        "signature_profile",
        "approval_id",
        "plan_hash",
        "approved_by",
        "approved_at",
        "signature",
    ]
    assert schema["properties"]["signature_profile"]["const"] == APPROVAL_SIGNATURE_PROFILE
    assert schema["properties"]["signature"] == {
        "maxLength": 64,
        "minLength": 64,
        "pattern": "^[a-f0-9]{64}$",
        "title": "Signature",
        "type": "string",
    }


@pytest.mark.parametrize(
    ("source", "canonical"),
    [
        ("2026-08-10T17:00:00Z", "2026-08-10T17:00:00+00:00"),
        ("2026-08-10T19:00:00.000001+02:00", "2026-08-10T17:00:00.000001+00:00"),
    ],
)
def test_timestamp_variants_are_framed_in_the_canonical_utc_form(
    source: str,
    canonical: str,
) -> None:
    payload = signed_receipt().model_dump(mode="json")
    payload["approved_at"] = source
    receipt = ApprovalReceipt.model_validate(payload)
    encoded = canonical.encode("utf-8")
    assert receipt.approved_at.isoformat() == canonical
    assert approval_signature_material(receipt).endswith(len(encoded).to_bytes(4, "big") + encoded)


def test_v1_length_prefixes_count_utf8_bytes() -> None:
    receipt = signed_receipt(approved_by="approuvé@example.com")
    values = (
        receipt.signature_profile,
        receipt.approval_id,
        receipt.plan_hash,
        receipt.approved_by,
        receipt.approved_at.isoformat(),
    )
    material = approval_signature_material(receipt)
    cursor = len(APPROVAL_SIGNATURE_DOMAIN)
    for value in values:
        field_length = int.from_bytes(material[cursor : cursor + 4], "big")
        cursor += 4
        encoded = value.encode("utf-8")
        assert field_length == len(encoded)
        assert material[cursor : cursor + field_length] == encoded
        cursor += field_length
    assert cursor == len(material)


def test_v1_does_not_apply_implicit_unicode_normalization() -> None:
    composed = signed_receipt(approved_by="approuvé@example.com")
    decomposed = signed_receipt(approved_by="approuve" + "\u0301" + "@example.com")
    assert composed.approved_by != decomposed.approved_by
    assert approval_signature_material(composed) != approval_signature_material(decomposed)


def test_v1_material_separates_the_legacy_collision_between_two_plans() -> None:
    other_plan = "b" * 64
    first = ApprovalReceipt(
        signature_profile=APPROVAL_SIGNATURE_PROFILE,
        approval_id="approval-0001",
        plan_hash=PLAN_HASH,
        approved_by=f"{other_plan}|approver@example.com",
        approved_at=NOW,
        signature="0" * 64,
    )
    # The current public schema already rejects the delimiter in approval_id.
    # Construct the former schema shape directly to keep the framing regression
    # independent from that additional input-validation defense.
    second = ApprovalReceipt.model_construct(
        signature_profile=APPROVAL_SIGNATURE_PROFILE,
        approval_id=f"approval-0001|{PLAN_HASH}",
        plan_hash=other_plan,
        approved_by="approver@example.com",
        approved_at=NOW,
        signature="0" * 64,
    )
    legacy_first = "|".join(
        [first.approval_id, first.plan_hash, first.approved_by, first.approved_at.isoformat()]
    )
    legacy_second = "|".join(
        [second.approval_id, second.plan_hash, second.approved_by, second.approved_at.isoformat()]
    )
    assert legacy_first == legacy_second
    assert approval_signature_material(first) != approval_signature_material(second)

    first_signature = hmac.new(
        SECRET.encode("utf-8"),
        approval_signature_material(first),
        hashlib.sha256,
    ).hexdigest()
    second = second.model_copy(update={"signature": first_signature})
    verifier = ApprovalVerifier(SECRET, DEFAULT_APPROVAL_MAX_AGE_SECONDS, now=lambda: NOW)
    assert not verifier.verify(second, other_plan)


def test_legacy_delimiter_signature_has_no_v1_fallback() -> None:
    receipt = signed_receipt()
    legacy_material = "|".join(
        [
            receipt.approval_id,
            receipt.plan_hash,
            receipt.approved_by,
            receipt.approved_at.isoformat(),
        ]
    ).encode("utf-8")
    legacy_signature = hmac.new(SECRET.encode("utf-8"), legacy_material, hashlib.sha256).hexdigest()
    receipt = receipt.model_copy(update={"signature": legacy_signature})
    verifier = ApprovalVerifier(SECRET, DEFAULT_APPROVAL_MAX_AGE_SECONDS, now=lambda: NOW)
    assert not verifier.verify(receipt, PLAN_HASH)


def test_signature_profile_is_required_and_unknown_profiles_are_rejected() -> None:
    payload = signed_receipt().model_dump(mode="json")
    payload.pop("signature_profile")
    with pytest.raises(ValidationError):
        ApprovalReceipt.model_validate(payload)
    payload["signature_profile"] = "hmac-sha256-legacy"
    with pytest.raises(ValidationError):
        ApprovalReceipt.model_validate(payload)


@pytest.mark.parametrize(
    "signature",
    ["A" * 64, "a" * 63, "g" * 64, "é" * 32, f" {'a' * 64} "],
)
def test_malformed_signatures_are_rejected_by_the_model(signature: str) -> None:
    payload = signed_receipt().model_dump(mode="json")
    payload["signature"] = signature
    with pytest.raises(ValidationError):
        ApprovalReceipt.model_validate(payload)


def test_whitespace_padded_profile_is_rejected_instead_of_normalized() -> None:
    payload = signed_receipt().model_dump(mode="json")
    payload["signature_profile"] = f" {APPROVAL_SIGNATURE_PROFILE} "
    with pytest.raises(ValidationError):
        ApprovalReceipt.model_validate(payload)


def test_verifier_rejects_bypassed_malformed_material_without_raising() -> None:
    verifier = ApprovalVerifier(SECRET, DEFAULT_APPROVAL_MAX_AGE_SECONDS, now=lambda: NOW)
    receipt = signed_receipt()
    assert not verifier.verify(
        receipt.model_copy(update={"signature": chr(233) * 32}),
        PLAN_HASH,
    )
    assert not verifier.verify(
        receipt.model_copy(update={"approved_by": "invalid-\ud800-identity"}),
        PLAN_HASH,
    )
    assert not verifier.verify(
        receipt.model_copy(update={"signature_profile": "hmac-sha256-legacy"}),
        PLAN_HASH,
    )
    assert not verifier.verify(
        receipt.model_copy(update={"signature_profile": object()}),
        PLAN_HASH,
    )


@pytest.mark.parametrize(
    "secret",
    [True, b"bytes", "invalid-\ud800-secret", "x", " " * 32],
)
def test_invalid_secret_material_fails_closed_at_startup(secret: object) -> None:
    with pytest.raises(ValueError):
        ApprovalVerifier(
            secret,  # type: ignore[arg-type]
            DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        )


def test_secret_bytes_are_used_exactly_without_trimming() -> None:
    exact_secret = " 12345678901234567890123456789012 "
    stripped_secret = exact_secret.strip()
    receipt = signed_receipt().model_copy(update={"signature": "0" * 64})
    signature = hmac.new(
        exact_secret.encode("utf-8"),
        approval_signature_material(receipt),
        hashlib.sha256,
    ).hexdigest()
    receipt = receipt.model_copy(update={"signature": signature})
    assert ApprovalVerifier(
        exact_secret,
        DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        now=lambda: NOW,
    ).verify(receipt, PLAN_HASH)
    assert not ApprovalVerifier(
        stripped_secret,
        DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        now=lambda: NOW,
    ).verify(receipt, PLAN_HASH)


@pytest.mark.parametrize(
    "approved_at",
    [
        0,
        1786381200,
        1786381200.123,
        "0",
        "1786381200",
        "1786381200.123",
        "0001-01-01T00:00:00+14:00",
        "9999-12-31T23:59:59-14:00",
    ],
)
def test_non_rfc3339_or_unrepresentable_timestamps_are_rejected(approved_at: object) -> None:
    payload = signed_receipt().model_dump(mode="json")
    payload["approved_at"] = approved_at
    with pytest.raises(ValidationError):
        ApprovalReceipt.model_validate(payload)


def test_naive_receipt_timestamp_is_rejected_by_the_model() -> None:
    with pytest.raises(ValidationError, match="must include a timezone"):
        ApprovalReceipt(
            signature_profile=APPROVAL_SIGNATURE_PROFILE,
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
