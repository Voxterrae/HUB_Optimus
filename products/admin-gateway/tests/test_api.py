import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import optimus_admin_gateway.main as main_module
from optimus_admin_gateway.approvals import ApprovalVerifier, approval_signature_material
from optimus_admin_gateway.main import app
from optimus_admin_gateway.models import APPROVAL_SIGNATURE_PROFILE, ApprovalReceipt

client = TestClient(app)
READER_HEADERS = {
    "x-optimus-dev-principal": "test-user",
    "x-optimus-dev-roles": "Optimus.Reader",
}
TENANT_ID = "11111111-1111-4111-8111-111111111111"
SUBJECT_ID = "33333333-3333-4333-8333-333333333333"
OID_CLAIM = "http://schemas.microsoft.com/identity/claims/objectidentifier"
TENANT_CLAIM = "http://schemas.microsoft.com/identity/claims/tenantid"
NAME_CLAIM = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
ROLE_CLAIM = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"


def easyauth_headers(*roles: str) -> dict[str, str]:
    payload = {
        "auth_typ": "aad",
        "claims": [
            {"typ": OID_CLAIM, "val": SUBJECT_ID},
            {"typ": TENANT_CLAIM, "val": TENANT_ID},
            {"typ": NAME_CLAIM, "val": "Integrated test principal"},
            *({"typ": ROLE_CLAIM, "val": role} for role in roles),
        ],
        "name_typ": NAME_CLAIM,
        "role_typ": ROLE_CLAIM,
    }
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return {"x-ms-client-principal": encoded}


PRODUCTION_READER_HEADERS = easyauth_headers("Optimus.Reader")
PRODUCTION_MUTATOR_HEADERS = easyauth_headers("Optimus.Reader", "Optimus.Mutator")
APPROVAL_SECRET = "synthetic-api-approval-secret-32-bytes"
APPROVAL_NOW = datetime(2026, 8, 10, 17, 0, tzinfo=timezone.utc)


def signed_approval(plan_hash: str, approved_at: datetime) -> dict[str, str]:
    receipt = ApprovalReceipt(
        signature_profile=APPROVAL_SIGNATURE_PROFILE,
        approval_id="approval-api-0001",
        plan_hash=plan_hash,
        approved_by="approver@example.com",
        approved_at=approved_at.astimezone(timezone.utc),
        signature="0" * 64,
    )
    signature = hmac.new(
        APPROVAL_SECRET.encode("utf-8"),
        approval_signature_material(receipt),
        hashlib.sha256,
    ).hexdigest()
    return receipt.model_copy(update={"signature": signature}).model_dump(mode="json")


def live_mutation_body(idempotency_key: str) -> dict:
    return {
        "parameters": {
            "mailbox": "pilot@example.com",
            "delegate": "owner@example.com",
            "automapping": False,
            "reason": "Restore delegated administrative access",
            "change_ticket": "CHG-APPROVAL",
        },
        "dry_run": False,
        "idempotency_key": idempotency_key,
    }


def test_health_is_public_and_safe() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["executor_mode"] == "disabled"


def test_internal_identity_headers_are_not_exposed_in_generated_openapi() -> None:
    schema = json.dumps(app.openapi()).lower()
    assert "x-ms-client-principal" not in schema
    assert "x-optimus-dev-principal" not in schema
    assert "x-optimus-dev-roles" not in schema


def test_operations_require_identity() -> None:
    response = client.get("/api/v1/operations")
    assert response.status_code == 401


def test_operations_require_reader_role() -> None:
    response = client.get(
        "/api/v1/operations",
        headers={"x-optimus-dev-principal": "test-user"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "ROLE_REQUIRED",
        "required_role": "Optimus.Reader",
    }


def test_legacy_role_header_is_not_trusted_in_dev_mode() -> None:
    response = client.get(
        "/api/v1/operations",
        headers={
            "x-optimus-dev-principal": "test-user",
            "x-optimus-roles": "Optimus.Reader",
        },
    )
    assert response.status_code == 403


def test_read_operation_dry_run() -> None:
    body = {
        "parameters": {"mailbox": "pilot@example.com"},
        "dry_run": True,
        "idempotency_key": "test-read-0001"
    }
    plan = client.post(
        "/api/v1/operations/exchange.diagnose_mailbox:plan",
        json=body,
        headers=PRODUCTION_READER_HEADERS,
    )
    assert plan.status_code == 200
    assert plan.json()["state"] == "PLANNED"
    execute = client.post(
        "/api/v1/operations/exchange.diagnose_mailbox:execute",
        json=body,
        headers=PRODUCTION_READER_HEADERS,
    )
    assert execute.status_code == 200
    assert execute.json()["dry_run"] is True


def test_mutation_defaults_to_dry_run() -> None:
    body = {
        "parameters": {
            "mailbox": "pilot@example.com",
            "delegate": "owner@example.com",
            "automapping": False,
            "reason": "Restore delegated administrative access",
            "change_ticket": "CHG-0001"
        },
        "idempotency_key": "test-mutate-0001"
    }
    response = client.post(
        "/api/v1/operations/exchange.grant_full_access:execute",
        json=body,
        headers=PRODUCTION_READER_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["state"] == "PLANNED"


def test_live_mutation_requires_mutator_role_before_approval() -> None:
    body = {
        "parameters": {
            "mailbox": "pilot@example.com",
            "delegate": "owner@example.com",
            "automapping": False,
            "reason": "Restore delegated administrative access",
            "change_ticket": "CHG-0002"
        },
        "dry_run": False,
        "idempotency_key": "test-mutate-0002"
    }
    response = client.post(
        "/api/v1/operations/exchange.grant_full_access:execute",
        json=body,
        headers=PRODUCTION_READER_HEADERS,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "ROLE_REQUIRED",
        "required_role": "Optimus.Mutator",
    }


def test_live_mutation_with_both_roles_reaches_approval_gate() -> None:
    body = {
        "parameters": {
            "mailbox": "pilot@example.com",
            "delegate": "owner@example.com",
            "automapping": False,
            "reason": "Restore delegated administrative access",
            "change_ticket": "CHG-0003",
        },
        "dry_run": False,
        "idempotency_key": "test-mutate-0003",
    }
    response = client.post(
        "/api/v1/operations/exchange.grant_full_access:execute",
        json=body,
        headers=PRODUCTION_MUTATOR_HEADERS,
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "APPROVAL_REQUIRED"


def test_boundary_approval_reaches_the_disabled_executor(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "approvals",
        ApprovalVerifier(APPROVAL_SECRET, max_age_seconds=900, now=lambda: APPROVAL_NOW),
    )
    body = live_mutation_body("test-approval-fresh-0001")
    plan = client.post(
        "/api/v1/operations/exchange.grant_full_access:plan",
        json=body,
        headers=PRODUCTION_MUTATOR_HEADERS,
    )
    assert plan.status_code == 200
    body["approval"] = signed_approval(
        plan.json()["plan_hash"],
        APPROVAL_NOW - timedelta(seconds=900),
    )

    response = client.post(
        "/api/v1/operations/exchange.grant_full_access:execute",
        json=body,
        headers=PRODUCTION_MUTATOR_HEADERS,
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "EXECUTOR_NOT_CONFIGURED"


@pytest.mark.parametrize(
    ("offset_seconds", "tamper_signature"),
    [(-901, False), (1, False), (0, True)],
)
def test_invalid_approvals_return_the_same_generic_response(
    monkeypatch,
    offset_seconds: int,
    tamper_signature: bool,
) -> None:
    monkeypatch.setattr(
        main_module,
        "approvals",
        ApprovalVerifier(APPROVAL_SECRET, max_age_seconds=900, now=lambda: APPROVAL_NOW),
    )
    body = live_mutation_body(f"test-approval-invalid-{offset_seconds}-{int(tamper_signature)}")
    plan = client.post(
        "/api/v1/operations/exchange.grant_full_access:plan",
        json=body,
        headers=PRODUCTION_MUTATOR_HEADERS,
    )
    assert plan.status_code == 200
    approval = signed_approval(
        plan.json()["plan_hash"],
        APPROVAL_NOW + timedelta(seconds=offset_seconds),
    )
    if tamper_signature:
        approval["signature"] = "0" * 64
    body["approval"] = approval

    response = client.post(
        "/api/v1/operations/exchange.grant_full_access:execute",
        json=body,
        headers=PRODUCTION_MUTATOR_HEADERS,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "APPROVAL_INVALID",
        "plan_hash": plan.json()["plan_hash"],
    }


def test_legacy_delimiter_signature_is_rejected_without_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "approvals",
        ApprovalVerifier(APPROVAL_SECRET, max_age_seconds=900, now=lambda: APPROVAL_NOW),
    )
    body = live_mutation_body("test-approval-legacy-0001")
    plan = client.post(
        "/api/v1/operations/exchange.grant_full_access:plan",
        json=body,
        headers=PRODUCTION_MUTATOR_HEADERS,
    )
    assert plan.status_code == 200
    approval = signed_approval(plan.json()["plan_hash"], APPROVAL_NOW)
    legacy_material = "|".join(
        [
            approval["approval_id"],
            approval["plan_hash"],
            approval["approved_by"],
            approval["approved_at"],
        ]
    ).encode("utf-8")
    approval["signature"] = hmac.new(
        APPROVAL_SECRET.encode("utf-8"),
        legacy_material,
        hashlib.sha256,
    ).hexdigest()
    body["approval"] = approval

    response = client.post(
        "/api/v1/operations/exchange.grant_full_access:execute",
        json=body,
        headers=PRODUCTION_MUTATOR_HEADERS,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "APPROVAL_INVALID",
        "plan_hash": plan.json()["plan_hash"],
    }


@pytest.mark.parametrize(
    "malformation",
    [
        "missing-profile",
        "unknown-profile",
        "unicode-signature",
        "numeric-timestamp",
        "epoch-string-timestamp",
        "underflow-timestamp",
        "overflow-timestamp",
    ],
)
def test_malformed_approval_contract_is_rejected_as_422(malformation: str) -> None:
    body = live_mutation_body(f"test-approval-malformed-{malformation}")
    plan = client.post(
        "/api/v1/operations/exchange.grant_full_access:plan",
        json=body,
        headers=PRODUCTION_MUTATOR_HEADERS,
    )
    assert plan.status_code == 200
    approval = signed_approval(plan.json()["plan_hash"], APPROVAL_NOW)
    if malformation == "missing-profile":
        approval.pop("signature_profile")
    elif malformation == "unknown-profile":
        approval["signature_profile"] = "hmac-sha256-legacy"
    elif malformation == "unicode-signature":
        approval["signature"] = chr(233) * 32
    elif malformation == "numeric-timestamp":
        approval["approved_at"] = 1786381200
    elif malformation == "epoch-string-timestamp":
        approval["approved_at"] = "1786381200"
    elif malformation == "underflow-timestamp":
        approval["approved_at"] = "0001-01-01T00:00:00+14:00"
    else:
        approval["approved_at"] = "9999-12-31T23:59:59-14:00"
    body["approval"] = approval

    response = client.post(
        "/api/v1/operations/exchange.grant_full_access:execute",
        json=body,
        headers=PRODUCTION_MUTATOR_HEADERS,
    )
    assert response.status_code == 422


def test_unknown_fields_are_rejected() -> None:
    body = {
        "parameters": {"mailbox": "pilot@example.com", "command": "Get-Anything"},
        "dry_run": True,
        "idempotency_key": "test-invalid-0001"
    }
    response = client.post(
        "/api/v1/operations/exchange.diagnose_mailbox:plan",
        json=body,
        headers=READER_HEADERS,
    )
    assert response.status_code == 422


def test_dataverse_alternate_key_identifiers_reject_odata_reserved_characters() -> None:
    body = {
        "parameters": {"mailbox": "pilot@example.com"},
        "dry_run": True,
        "idempotency_key": "request:0001",
    }
    response = client.post(
        "/api/v1/operations/exchange.diagnose_mailbox:plan",
        json=body,
        headers=PRODUCTION_READER_HEADERS,
    )
    assert response.status_code == 422

    safe_body = {
        "parameters": {"mailbox": "pilot@example.com"},
        "dry_run": True,
        "idempotency_key": "request.0001-safe",
    }
    safe_response = client.post(
        "/api/v1/operations/exchange.diagnose_mailbox:plan",
        json=safe_body,
        headers=PRODUCTION_READER_HEADERS,
    )
    assert safe_response.status_code == 200
