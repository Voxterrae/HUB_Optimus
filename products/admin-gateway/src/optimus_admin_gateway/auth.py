from __future__ import annotations

import base64
import binascii
import json
from typing import Any
from uuid import UUID

from fastapi import Header, HTTPException, status
from pydantic import ValidationError

from .config import Settings
from .models import Principal

AAD_AUTH_TYPE = "aad"
OBJECT_ID_CLAIM_TYPES = frozenset(
    {
        "oid",
        "http://schemas.microsoft.com/identity/claims/objectidentifier",
    }
)
TENANT_ID_CLAIM_TYPES = frozenset(
    {
        "tid",
        "http://schemas.microsoft.com/identity/claims/tenantid",
    }
)
ROLE_CLAIM_TYPES = frozenset(
    {
        "roles",
        "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
    }
)
MAX_PRINCIPAL_HEADER_BYTES = 32_768
MAX_CLAIMS = 256


class _DuplicateJsonKey(ValueError):
    pass


def _reject_auth(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": message},
    )


def _load_unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(key)
        result[key] = value
    return result


def _single_claim(
    claims: list[tuple[str, str]],
    claim_types: frozenset[str],
    *,
    required: bool,
    label: str,
) -> str | None:
    values = [value for claim_type, value in claims if claim_type in claim_types]
    if not values and not required:
        return None
    if len(values) != 1:
        raise _reject_auth("AUTH_INVALID", f"EasyAuth principal must contain one unambiguous {label} claim")
    return values[0]


def _normalize_uuid(value: str, *, code: str, message: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise _reject_auth(code, message) from exc


def _normalize_configured_tenant(value: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AUTH_NOT_CONFIGURED",
                "message": "Configured Entra tenant ID is invalid",
            },
        ) from exc


def parse_easyauth_principal(encoded_principal: str, expected_tenant_id: str) -> Principal:
    if not encoded_principal or len(encoded_principal) > MAX_PRINCIPAL_HEADER_BYTES:
        raise _reject_auth("AUTH_INVALID", "EasyAuth principal header is missing or too large")

    try:
        decoded = base64.b64decode(encoded_principal, validate=True)
        payload = json.loads(decoded.decode("utf-8"), object_pairs_hook=_load_unique_object)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey) as exc:
        raise _reject_auth("AUTH_INVALID", "EasyAuth principal header is malformed") from exc

    if not isinstance(payload, dict):
        raise _reject_auth("AUTH_INVALID", "EasyAuth principal payload must be an object")
    if payload.get("auth_typ") != AAD_AUTH_TYPE:
        raise _reject_auth("AUTH_INVALID", "Microsoft Entra authentication is required")

    role_type = payload.get("role_typ")
    name_type = payload.get("name_typ")
    raw_claims = payload.get("claims")
    if not isinstance(role_type, str) or not role_type:
        raise _reject_auth("AUTH_INVALID", "EasyAuth role claim type is missing")
    if role_type not in ROLE_CLAIM_TYPES:
        raise _reject_auth("AUTH_INVALID", "EasyAuth role claim type is not recognized")
    if not isinstance(name_type, str) or not name_type:
        raise _reject_auth("AUTH_INVALID", "EasyAuth name claim type is missing")
    if not isinstance(raw_claims, list) or len(raw_claims) > MAX_CLAIMS:
        raise _reject_auth("AUTH_INVALID", "EasyAuth claims must be a bounded array")

    claims: list[tuple[str, str]] = []
    for claim in raw_claims:
        if not isinstance(claim, dict) or set(claim) != {"typ", "val"}:
            raise _reject_auth("AUTH_INVALID", "EasyAuth claim shape is invalid")
        claim_type = claim.get("typ")
        claim_value = claim.get("val")
        if not isinstance(claim_type, str) or not claim_type or not isinstance(claim_value, str) or not claim_value:
            raise _reject_auth("AUTH_INVALID", "EasyAuth claim values must be non-empty strings")
        claims.append((claim_type, claim_value))

    subject_id = _single_claim(
        claims,
        OBJECT_ID_CLAIM_TYPES,
        required=True,
        label="object ID",
    )
    tenant_id = _single_claim(
        claims,
        TENANT_ID_CLAIM_TYPES,
        required=True,
        label="tenant ID",
    )
    if subject_id is None or tenant_id is None:
        raise _reject_auth("AUTH_INVALID", "EasyAuth identity claims are missing")
    normalized_subject = _normalize_uuid(
        subject_id,
        code="AUTH_INVALID",
        message="EasyAuth object ID claim is invalid",
    )
    normalized_tenant = _normalize_uuid(
        tenant_id,
        code="AUTH_INVALID",
        message="EasyAuth tenant ID claim is invalid",
    )
    configured_tenant = _normalize_configured_tenant(expected_tenant_id)
    if normalized_tenant != configured_tenant:
        raise _reject_auth("TENANT_MISMATCH", "Authenticated principal belongs to a different tenant")

    display_name = _single_claim(
        claims,
        frozenset({name_type}),
        required=False,
        label="display name",
    )
    roles = {value for claim_type, value in claims if claim_type == role_type}
    try:
        return Principal(subject_id=normalized_subject, display_name=display_name, roles=roles)
    except ValidationError as exc:
        raise _reject_auth("AUTH_INVALID", "EasyAuth principal claims are invalid") from exc


def build_principal_dependency(settings: Settings):
    async def get_principal(
        x_ms_client_principal: str | None = Header(default=None, include_in_schema=False),
        x_optimus_dev_principal: str | None = Header(default=None, include_in_schema=False),
        x_optimus_dev_roles: str | None = Header(default=None, include_in_schema=False),
    ) -> Principal:
        if x_ms_client_principal:
            if settings.entra_tenant_id is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "code": "AUTH_NOT_CONFIGURED",
                        "message": "Entra tenant binding is not configured",
                    },
                )
            return parse_easyauth_principal(x_ms_client_principal, settings.entra_tenant_id)
        if settings.dev_mode and x_optimus_dev_principal:
            roles = {role.strip() for role in (x_optimus_dev_roles or "").split(",") if role.strip()}
            return Principal(subject_id=x_optimus_dev_principal, display_name="Local developer", roles=roles)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Authenticated Entra principal required"},
        )

    return get_principal
