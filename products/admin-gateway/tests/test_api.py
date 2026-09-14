import base64
import json

from fastapi.testclient import TestClient

from optimus_admin_gateway.main import app

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


def mutation_request() -> dict:
    return {
        "parameters": {
            "mailbox": "pilot@example.invalid",
            "delegate": "owner@example.invalid",
            "automapping": False,
            "reason": "Synthetic reviewed access change",
            "change_ticket": "SYNTHETIC-001",
        },
        "dry_run": True,
        "idempotency_key": "synthetic-plan-001",
    }


def test_plan_hash_is_stable_across_execution_mode() -> None:
    body = mutation_request()
    route = "/api/v1/operations/exchange.grant_full_access:plan"
    preview = client.post(route, json=body, headers=PRODUCTION_READER_HEADERS)
    body["dry_run"] = False
    intended = client.post(route, json=body, headers=PRODUCTION_READER_HEADERS)
    assert preview.status_code == intended.status_code == 200
    assert preview.json()["plan_hash"] == intended.json()["plan_hash"]
    assert preview.json()["state"] == "PLANNED"
    assert intended.json()["state"] == "APPROVAL_REQUIRED"


def test_approved_preview_reaches_disabled_executor_and_changed_plan_is_rejected(
    monkeypatch,
) -> None:
    import hashlib
    import hmac
    from datetime import datetime, timezone

    from optimus_admin_gateway import main as gateway
    from optimus_admin_gateway.approvals import ApprovalVerifier

    # A synthetic receipt exercises only the reference executor, which remains
    # disabled. This test cannot call Exchange, Azure or a tenant adapter.
    secret = "synthetic-test-only-receipt-key"
    monkeypatch.setattr(gateway, "approvals", ApprovalVerifier(secret))
    body = mutation_request()
    planned = client.post(
        "/api/v1/operations/exchange.grant_full_access:plan",
        json=body, headers=PRODUCTION_READER_HEADERS,
    )
    assert planned.status_code == 200
    receipt = {
        "approval_id": "synthetic-approval-001",
        "plan_hash": planned.json()["plan_hash"],
        "approved_by": "synthetic-test-approver",
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    material = "|".join(receipt[key] for key in (
        "approval_id", "plan_hash", "approved_by", "approved_at",
    )).encode()
    receipt["signature"] = hmac.new(secret.encode(), material, hashlib.sha256).hexdigest()
    body["approval"] = receipt
    body["dry_run"] = False
    route = "/api/v1/operations/exchange.grant_full_access:execute"
    accepted = client.post(route, json=body, headers=PRODUCTION_MUTATOR_HEADERS)
    assert accepted.status_code == 503
    assert accepted.json()["detail"]["code"] == "EXECUTOR_NOT_CONFIGURED"
    body["parameters"]["delegate"] = "different@example.invalid"
    rejected = client.post(route, json=body, headers=PRODUCTION_MUTATOR_HEADERS)
    assert rejected.status_code == 403
    assert rejected.json()["detail"]["code"] == "APPROVAL_INVALID"


def test_risk_and_catalog_version_changes_invalidate_plan_hash(monkeypatch) -> None:
    from optimus_admin_gateway import main as gateway
    from optimus_admin_gateway.models import RiskLevel

    route = "/api/v1/operations/exchange.grant_full_access:plan"
    body = mutation_request()
    initial = client.post(route, json=body, headers=PRODUCTION_READER_HEADERS)
    assert initial.status_code == 200
    original = initial.json()["plan_hash"]
    definition = gateway.catalog.get("exchange.grant_full_access")
    with monkeypatch.context() as patch:
        patch.setattr(definition, "risk", RiskLevel.medium)
        changed = client.post(route, json=body, headers=PRODUCTION_READER_HEADERS)
        assert changed.status_code == 200
        assert changed.json()["plan_hash"] != original
    with monkeypatch.context() as patch:
        patch.setattr(gateway.catalog, "version", "synthetic-next-version")
        changed = client.post(route, json=body, headers=PRODUCTION_READER_HEADERS)
        assert changed.status_code == 200
        assert changed.json()["plan_hash"] != original


def test_parameter_validator_errors_are_serializable_422_responses() -> None:
    for field, value in (("mailbox", "invalid"), ("delegate", "invalid"), ("reason", "x")):
        body = mutation_request()
        body["parameters"][field] = value
        response = client.post(
            "/api/v1/operations/exchange.grant_full_access:plan",
            json=body, headers=PRODUCTION_READER_HEADERS,
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "PARAMETER_VALIDATION_FAILED"
        assert response.json()["detail"]["errors"]
