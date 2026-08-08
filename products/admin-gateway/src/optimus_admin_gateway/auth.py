from __future__ import annotations

from fastapi import Header, HTTPException, status

from .config import Settings
from .models import Principal


def build_principal_dependency(settings: Settings):
    async def get_principal(
        x_ms_client_principal_id: str | None = Header(default=None),
        x_ms_client_principal_name: str | None = Header(default=None),
        x_optimus_roles: str | None = Header(default=None),
        x_optimus_dev_principal: str | None = Header(default=None),
    ) -> Principal:
        if x_ms_client_principal_id:
            roles = {role.strip() for role in (x_optimus_roles or "").split(",") if role.strip()}
            return Principal(
                subject_id=x_ms_client_principal_id,
                display_name=x_ms_client_principal_name,
                roles=roles,
            )
        if settings.dev_mode and x_optimus_dev_principal:
            roles = {role.strip() for role in (x_optimus_roles or "").split(",") if role.strip()}
            return Principal(subject_id=x_optimus_dev_principal, display_name="Local developer", roles=roles)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Authenticated Entra principal required"},
        )

    return get_principal
