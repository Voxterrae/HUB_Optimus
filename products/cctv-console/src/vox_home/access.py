"""Core-only access contexts and revocable, in-memory delegated permissions.

These objects are issued inside the trusted app, never deserialized from a
plugin request. The app supplies ``owners`` from its trusted local identity
provider. Constructing an AccessContext is not a login or OS authentication.
"""

from dataclasses import dataclass, replace
from threading import RLock

from .contracts import (
    ContractValidationError, PERMISSION_OPERATIONS, _epoch, _identifier, _operations,
)


class AccessDenied(PermissionError):
    """A refusal with a safe, machine-readable reason (no private inputs)."""

    def __init__(self, code: str = "access_denied"):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class AccessContext:
    site_id: str
    principal_id: str
    grant_id: str | None

    def __post_init__(self) -> None:
        _identifier(self.site_id, "site_id")
        _identifier(self.principal_id, "principal_id")
        if self.grant_id is not None:
            _identifier(self.grant_id, "grant_id")


@dataclass(frozen=True)
class Grant:
    grant_id: str
    site_id: str
    principal_id: str
    device_ids: tuple[str, ...]
    operations: tuple[str, ...]
    expires_at: float
    revoked: bool

    def __post_init__(self) -> None:
        for field in ("grant_id", "site_id", "principal_id"):
            _identifier(getattr(self, field), field)
        if not isinstance(self.device_ids, tuple):
            raise ContractValidationError("invalid_type", "device_ids")
        if not self.device_ids:
            raise ContractValidationError("invalid_value", "device_ids")
        for device_id in self.device_ids:
            _identifier(device_id, "device_ids")
        if len(set(self.device_ids)) != len(self.device_ids):
            raise ContractValidationError("duplicate_device", "device_ids")
        _operations(self.operations, "operations")
        if not self.operations:
            raise ContractValidationError("invalid_value", "operations")
        _epoch(self.expires_at, "expires_at")
        if type(self.revoked) is not bool:
            raise ContractValidationError("invalid_type", "revoked")


class AccessService:
    """Exact site/principal/device/operation grants; restart forgets all grants.

    Owners have access only within their own site. Delegated contexts, including
    an owner with a grant ID, must satisfy their grant. No master identity is
    inferred across installations. Grant IDs cannot be reused during a run.
    """

    def __init__(self, owners: dict[str, str]):
        if type(owners) is not dict:
            raise ContractValidationError("invalid_type", "owners")
        for site_id, principal_id in owners.items():
            _identifier(site_id, "site_id")
            _identifier(principal_id, "principal_id")
        self._owners = dict(owners)
        self._grants: dict[str, Grant] = {}
        self._lock = RLock()

    def _owner(self, context: AccessContext, site_id: str) -> None:
        if (type(context) is not AccessContext or context.grant_id is not None
                or context.site_id != site_id
                or self._owners.get(site_id) != context.principal_id):
            raise AccessDenied("owner_required")

    def issue_grant(self, owner: AccessContext, grant: Grant) -> None:
        if type(grant) is not Grant:
            raise AccessDenied("invalid_grant")
        with self._lock:
            self._owner(owner, grant.site_id)
            if grant.grant_id in self._grants:
                raise AccessDenied("grant_id_used")
            self._grants[grant.grant_id] = grant

    def require(self, context: AccessContext, device_id: str, operation: str, now: float) -> None:
        if type(context) is not AccessContext:
            raise AccessDenied("invalid_context")
        try:
            _identifier(device_id, "device_id")
            _epoch(now, "now")
        except ContractValidationError:
            raise AccessDenied("invalid_request") from None
        if not isinstance(operation, str) or operation not in PERMISSION_OPERATIONS:
            raise AccessDenied("unknown_operation")
        with self._lock:
            if context.grant_id is None:
                self._owner(context, context.site_id)
                return
            grant = self._grants.get(context.grant_id)
            if (grant is None or grant.revoked or now >= grant.expires_at
                    or grant.site_id != context.site_id
                    or grant.principal_id != context.principal_id
                    or device_id not in grant.device_ids or operation not in grant.operations):
                raise AccessDenied()

    def revoke(self, owner: AccessContext, grant_id: str) -> None:
        if type(owner) is not AccessContext:
            raise AccessDenied("invalid_context")
        try:
            _identifier(grant_id, "grant_id")
        except ContractValidationError:
            raise AccessDenied("invalid_grant") from None
        with self._lock:
            grant = self._grants.get(grant_id)
            if grant is None:
                raise AccessDenied("unknown_grant")
            self._owner(owner, grant.site_id)
            self._grants[grant_id] = replace(grant, revoked=True)
