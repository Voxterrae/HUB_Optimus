from fastapi.testclient import TestClient

from optimus_admin_gateway.main import app

client = TestClient(app)
HEADERS = {"x-optimus-dev-principal": "test-user", "x-optimus-roles": "Optimus.Reader"}


def test_health_is_public_and_safe() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["executor_mode"] == "disabled"


def test_operations_require_identity() -> None:
    response = client.get("/api/v1/operations")
    assert response.status_code == 401


def test_read_operation_dry_run() -> None:
    body = {
        "parameters": {"mailbox": "pilot@example.com"},
        "dry_run": True,
        "idempotency_key": "test-read-0001"
    }
    plan = client.post("/api/v1/operations/exchange.diagnose_mailbox:plan", json=body, headers=HEADERS)
    assert plan.status_code == 200
    assert plan.json()["state"] == "PLANNED"
    execute = client.post("/api/v1/operations/exchange.diagnose_mailbox:execute", json=body, headers=HEADERS)
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
    response = client.post("/api/v1/operations/exchange.grant_full_access:execute", json=body, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["state"] == "PLANNED"


def test_live_mutation_without_approval_is_rejected() -> None:
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
    response = client.post("/api/v1/operations/exchange.grant_full_access:execute", json=body, headers=HEADERS)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "APPROVAL_REQUIRED"


def test_unknown_fields_are_rejected() -> None:
    body = {
        "parameters": {"mailbox": "pilot@example.com", "command": "Get-Anything"},
        "dry_run": True,
        "idempotency_key": "test-invalid-0001"
    }
    response = client.post("/api/v1/operations/exchange.diagnose_mailbox:plan", json=body, headers=HEADERS)
    assert response.status_code == 422
