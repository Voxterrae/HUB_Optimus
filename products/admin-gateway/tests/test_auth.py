from __future__ import annotations

import base64
import json
import warnings
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette import exceptions as starlette_exceptions

from optimus_admin_gateway.auth import build_principal_dependency
from optimus_admin_gateway.config import Settings
from optimus_admin_gateway.models import Principal

TENANT_ID = "11111111-1111-4111-8111-111111111111"
OTHER_TENANT_ID = "22222222-2222-4222-8222-222222222222"
SUBJECT_ID = "33333333-3333-4333-8333-333333333333"
OID_CLAIM = "http://schemas.microsoft.com/identity/claims/objectidentifier"
TENANT_CLAIM = "http://schemas.microsoft.com/identity/claims/tenantid"
NAME_CLAIM = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
ROLE_CLAIM = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"


def make_settings(*, dev_mode: bool = False, tenant_id: str | None = TENANT_ID) -> Settings:
    return Settings(
        dev_mode=dev_mode,
        catalog_path=Path("unused.json"),
        executor_mode="disabled",
        approval_hmac_secret=None,
        entra_tenant_id=tenant_id,
        reader_role="Optimus.Reader",
        mutator_role="Optimus.Mutator",
    )


def encode_principal(
    *,
    tenant_id: str = TENANT_ID,
    auth_type: str = "aad",
    roles: tuple[str, ...] = ("Optimus.Reader",),
    extra_claims: tuple[dict[str, str], ...] = (),
    role_type: str = ROLE_CLAIM,
) -> str:
    claims = [
        {"typ": OID_CLAIM, "val": SUBJECT_ID},
        {"typ": TENANT_CLAIM, "val": tenant_id},
        {"typ": NAME_CLAIM, "val": "Test principal"},
        *({"typ": role_type, "val": role} for role in roles),
        *extra_claims,
    ]
    payload = {
        "auth_typ": auth_type,
        "claims": claims,
        "name_typ": NAME_CLAIM,
        "role_typ": role_type,
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def make_client(settings: Settings) -> TestClient:
    test_app = FastAPI()
    get_principal = build_principal_dependency(settings)

    @test_app.get("/principal")
    async def principal_view(principal: Principal = Depends(get_principal)) -> dict:
        return {
            "subject_id": principal.subject_id,
            "display_name": principal.display_name,
            "roles": sorted(principal.roles),
        }

    return TestClient(test_app)


def test_valid_easyauth_principal_uses_oid_tenant_and_canonical_roles() -> None:
    response = make_client(make_settings()).get(
        "/principal",
        headers={"x-ms-client-principal": encode_principal(roles=("Optimus.Reader", "Optimus.Mutator"))},
    )
    assert response.status_code == 200
    assert response.json() == {
        "subject_id": SUBJECT_ID,
        "display_name": "Test principal",
        "roles": ["Optimus.Mutator", "Optimus.Reader"],
    }


@pytest.mark.parametrize("principal", ["not-base64", base64.b64encode(b"not-json").decode("ascii")])
def test_malformed_easyauth_principal_is_rejected(principal: str) -> None:
    response = make_client(make_settings()).get(
        "/principal",
        headers={"x-ms-client-principal": principal},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_INVALID"


def test_non_aad_principal_is_rejected() -> None:
    response = make_client(make_settings()).get(
        "/principal",
        headers={"x-ms-client-principal": encode_principal(auth_type="github")},
    )
    assert response.status_code == 401


def test_principal_from_another_tenant_is_rejected() -> None:
    response = make_client(make_settings()).get(
        "/principal",
        headers={"x-ms-client-principal": encode_principal(tenant_id=OTHER_TENANT_ID)},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "TENANT_MISMATCH"


def test_ambiguous_object_id_claim_is_rejected() -> None:
    response = make_client(make_settings()).get(
        "/principal",
        headers={
            "x-ms-client-principal": encode_principal(
                extra_claims=({"typ": "oid", "val": "44444444-4444-4444-8444-444444444444"},),
            )
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_INVALID"


def test_duplicate_object_id_claim_is_rejected_even_when_value_matches() -> None:
    response = make_client(make_settings()).get(
        "/principal",
        headers={
            "x-ms-client-principal": encode_principal(
                extra_claims=({"typ": "oid", "val": SUBJECT_ID},),
            )
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_INVALID"


def test_duplicate_json_key_is_rejected() -> None:
    decoded = base64.b64decode(encode_principal()).decode("utf-8")
    duplicated = decoded.replace('"auth_typ": "aad"', '"auth_typ": "aad", "auth_typ": "aad"', 1)
    encoded = base64.b64encode(duplicated.encode("utf-8")).decode("ascii")
    response = make_client(make_settings()).get(
        "/principal",
        headers={"x-ms-client-principal": encoded},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_INVALID"


def test_production_auth_fails_closed_without_tenant_binding() -> None:
    response = make_client(make_settings(tenant_id=None)).get(
        "/principal",
        headers={"x-ms-client-principal": encode_principal()},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "AUTH_NOT_CONFIGURED"


def test_production_auth_fails_closed_with_invalid_tenant_binding() -> None:
    response = make_client(make_settings(tenant_id="not-a-tenant-id")).get(
        "/principal",
        headers={"x-ms-client-principal": encode_principal()},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "AUTH_NOT_CONFIGURED"


def test_legacy_identity_and_role_headers_do_not_authenticate() -> None:
    response = make_client(make_settings()).get(
        "/principal",
        headers={
            "x-ms-client-principal-id": SUBJECT_ID,
            "x-optimus-roles": "Optimus.Reader",
        },
    )
    assert response.status_code == 401


def test_client_controlled_role_header_is_ignored() -> None:
    response = make_client(make_settings()).get(
        "/principal",
        headers={
            "x-ms-client-principal": encode_principal(roles=()),
            "x-optimus-roles": "Optimus.Mutator",
        },
    )
    assert response.status_code == 200
    assert response.json()["roles"] == []


def test_claim_outside_declared_role_type_is_ignored() -> None:
    response = make_client(make_settings()).get(
        "/principal",
        headers={
            "x-ms-client-principal": encode_principal(
                roles=(),
                extra_claims=({"typ": "roles", "val": "Optimus.Mutator"},),
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["roles"] == []


def test_unrecognized_role_claim_type_is_rejected() -> None:
    response = make_client(make_settings()).get(
        "/principal",
        headers={"x-ms-client-principal": encode_principal(role_type="custom-role")},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_INVALID"


def test_dev_headers_are_available_only_in_dev_mode() -> None:
    headers = {
        "x-optimus-dev-principal": "local-user",
        "x-optimus-dev-roles": "Optimus.Reader",
    }
    denied = make_client(make_settings(dev_mode=False)).get("/principal", headers=headers)
    allowed = make_client(make_settings(dev_mode=True, tenant_id=None)).get("/principal", headers=headers)
    assert denied.status_code == 401
    assert allowed.status_code == 200
    assert allowed.json()["roles"] == ["Optimus.Reader"]


def test_reader_and_mutator_roles_cannot_collapse() -> None:
    with pytest.raises(ValueError, match="must remain separate"):
        Settings(
            dev_mode=False,
            catalog_path=Path("unused.json"),
            executor_mode="disabled",
            approval_hmac_secret=None,
            entra_tenant_id=TENANT_ID,
            reader_role="Optimus.Reader",
            mutator_role="Optimus.Reader",
        )


def test_testclient_deprecation_is_fatal_when_available() -> None:
    warning_type = getattr(starlette_exceptions, "StarletteDeprecationWarning", None)
    if warning_type is None:
        pytest.skip("This supported Starlette version predates the TestClient warning type")
    with pytest.raises(warning_type):
        warnings.warn("warning policy probe", warning_type, stacklevel=1)
