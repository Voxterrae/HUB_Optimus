"""Pure, immutable records for the versioned Home adapter boundary.

Contract timestamps are UTC epoch seconds. An entrypoint is an import
identifier only; validation never imports or executes adapter code.
"""

from dataclasses import dataclass
from collections.abc import Iterator
import keyword
import math
import re
from typing import Protocol


API_MAJOR = 1
PERMISSION_OPERATIONS = (
    "probe", "health", "events", "snapshot", "recordings", "playback",
    "prepare_action", "execute_action", "metadata_read", "evidence_read",
    "credential_use",
)
CAPABILITY_STATUSES = ("verified", "advertised", "pending", "unsupported")


class ContractValidationError(ValueError):
    """Invalid boundary input, with a stable machine-readable code and field."""

    def __init__(self, code: str, field: str):
        self.code = code
        self.field = field
        super().__init__(f"{code}: {field}")


def _text(value: str | None, field: str, *, optional: bool = False) -> None:
    if optional and value is None:
        return
    if not isinstance(value, str):
        raise ContractValidationError("invalid_type", field)
    if not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ContractValidationError("invalid_value", field)


def _identifier(value: str, field: str) -> None:
    _text(value, field)
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", value):
        raise ContractValidationError("invalid_value", field)


def _epoch(value: float | None, field: str, *, optional: bool = False) -> None:
    if optional and value is None:
        return
    if type(value) not in (int, float):
        raise ContractValidationError("invalid_type", field)
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ContractValidationError("invalid_value", field)


def _operations(value: tuple[str, ...], field: str) -> None:
    if not isinstance(value, tuple):
        raise ContractValidationError("invalid_type", field)
    seen = set()
    for operation in value:
        if not isinstance(operation, str):
            raise ContractValidationError("invalid_type", field)
        if operation not in PERMISSION_OPERATIONS:
            raise ContractValidationError("unknown_operation", field)
        if operation in seen:
            raise ContractValidationError("duplicate_operation", field)
        seen.add(operation)


def _record_tuple(value: tuple, field: str, record_type: type) -> None:
    if not isinstance(value, tuple) or any(not isinstance(item, record_type) for item in value):
        raise ContractValidationError("invalid_type", field)


def _mapping_fields(mapping: dict, fields: tuple[str, ...], field: str) -> None:
    if not isinstance(mapping, dict):
        raise ContractValidationError("invalid_type", field)
    for name in fields:
        if name not in mapping:
            raise ContractValidationError("missing_field", name)
    if any(name not in fields for name in mapping):
        # The unknown key itself may contain private material: never echo it.
        raise ContractValidationError("unknown_field", field)


def _entrypoint(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*", value):
        raise ContractValidationError("invalid_entrypoint", "entrypoint")
    if any(keyword.iskeyword(part) for part in value.replace(":", ".").split(".")):
        raise ContractValidationError("invalid_entrypoint", "entrypoint")


@dataclass(frozen=True)
class Target:
    site_id: str
    device_id: str
    host: str
    expected_serial: str | None

    def __post_init__(self) -> None:
        _identifier(self.site_id, "site_id")
        _identifier(self.device_id, "device_id")
        _text(self.host, "host")
        _text(self.expected_serial, "expected_serial", optional=True)


@dataclass(frozen=True)
class Capability:
    name: str
    status: str
    proof: str | None
    checked_at: float | None

    def __post_init__(self) -> None:
        _identifier(self.name, "name")
        _text(self.status, "status")
        if self.status not in CAPABILITY_STATUSES:
            raise ContractValidationError("invalid_value", "status")
        _text(self.proof, "proof", optional=True)
        _epoch(self.checked_at, "checked_at", optional=True)
        if self.status == "verified" and self.proof is None:
            raise ContractValidationError("verification_requires_proof", "proof")


@dataclass(frozen=True)
class DeviceRecord:
    site_id: str
    device_id: str
    model: str | None
    firmware: str | None
    adapter_id: str
    capabilities: tuple[Capability, ...]
    checked_at: float

    def __post_init__(self) -> None:
        _identifier(self.site_id, "site_id")
        _identifier(self.device_id, "device_id")
        _text(self.model, "model", optional=True)
        _text(self.firmware, "firmware", optional=True)
        _identifier(self.adapter_id, "adapter_id")
        _record_tuple(self.capabilities, "capabilities", Capability)
        _epoch(self.checked_at, "checked_at")


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    site_id: str
    device_id: str
    channel: int | None
    kind: str
    status: str
    device_time: str | None
    received_at: float

    def __post_init__(self) -> None:
        _identifier(self.event_id, "event_id")
        _identifier(self.site_id, "site_id")
        _identifier(self.device_id, "device_id")
        if self.channel is not None:
            if type(self.channel) is not int:
                raise ContractValidationError("invalid_type", "channel")
            if self.channel < 1:
                raise ContractValidationError("invalid_value", "channel")
        _text(self.kind, "kind")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", self.kind):
            raise ContractValidationError("invalid_value", "kind")
        _text(self.status, "status")
        if self.status not in ("Start", "Stop", "None"):
            raise ContractValidationError("invalid_value", "status")
        _text(self.device_time, "device_time", optional=True)
        _epoch(self.received_at, "received_at")


@dataclass(frozen=True)
class EvidenceRef:
    """An opaque asset ID and provenance; never an image path or pixel block."""

    asset_id: str
    provenance: str
    state: str

    def __post_init__(self) -> None:
        _identifier(self.asset_id, "asset_id")
        _text(self.provenance, "provenance")
        _text(self.state, "state")


@dataclass(frozen=True)
class ActionProposal:
    """A plan awaiting independent execution and authorization.

    The parameter mapping is copied; its arbitrary object values remain
    caller-defined. Frozen records do not imply deep object immutability.
    """

    proposal_id: str
    target: Target
    action: str
    parameters: dict[str, object]
    effect: str
    reason: str
    required_operations: tuple[str, ...]
    expires_at: float

    def __post_init__(self) -> None:
        _identifier(self.proposal_id, "proposal_id")
        if not isinstance(self.target, Target):
            raise ContractValidationError("invalid_type", "target")
        _identifier(self.action, "action")
        if not isinstance(self.parameters, dict):
            raise ContractValidationError("invalid_type", "parameters")
        for key in self.parameters:
            _text(key, "parameters")
        _text(self.effect, "effect")
        _text(self.reason, "reason")
        _operations(self.required_operations, "required_operations")
        _epoch(self.expires_at, "expires_at")
        object.__setattr__(self, "parameters", dict(self.parameters))


@dataclass(frozen=True)
class OperationResult:
    status: str
    value: object | None
    reason: str | None

    def __post_init__(self) -> None:
        _text(self.status, "status")
        _text(self.reason, "reason", optional=True)
        if self.status == "unsupported":
            if self.reason is None:
                raise ContractValidationError("invalid_value", "reason")
            if self.value is not None:
                raise ContractValidationError("invalid_value", "value")


@dataclass(frozen=True)
class AdapterManifest:
    adapter_id: str
    version: str
    api_major: int
    entrypoint: str
    permissions: tuple[str, ...]
    allowed_targets: tuple[Target, ...]

    def __post_init__(self) -> None:
        _identifier(self.adapter_id, "adapter_id")
        _text(self.version, "version")
        if type(self.api_major) is not int:
            raise ContractValidationError("invalid_type", "api_major")
        if self.api_major != API_MAJOR:
            raise ContractValidationError("incompatible_api", "api_major")
        _entrypoint(self.entrypoint)
        _operations(self.permissions, "permissions")
        _record_tuple(self.allowed_targets, "allowed_targets", Target)


def validate_manifest(mapping: dict) -> AdapterManifest:
    """Validate a JSON-shaped manifest without loading its adapter."""
    fields = ("adapter_id", "version", "api_major", "entrypoint", "permissions", "allowed_targets")
    _mapping_fields(mapping, fields, "manifest")
    for field in ("permissions", "allowed_targets"):
        if not isinstance(mapping[field], (list, tuple)):
            raise ContractValidationError("invalid_type", field)
    targets = []
    for target in mapping["allowed_targets"]:
        if not isinstance(target, Target):
            target_fields = ("site_id", "device_id", "host", "expected_serial")
            _mapping_fields(target, target_fields, "allowed_targets")
            target = Target(**target)
        targets.append(target)
    return AdapterManifest(
        mapping["adapter_id"], mapping["version"], mapping["api_major"],
        mapping["entrypoint"], tuple(mapping["permissions"]), tuple(targets),
    )


class Adapter(Protocol):
    """Adapter interface; unsupported operations return a reasoned result.

    Return ``OperationResult('unsupported', None, reason)`` for an unavailable
    operation. ``prepare_action`` only proposes; ``execute_action`` performs
    separately authorized work. Event and recording permissions are named
    ``events`` and ``recordings`` respectively. Image results use EvidenceRef.
    """

    def probe(self, target: Target) -> DeviceRecord | OperationResult: ...

    def health(self) -> OperationResult: ...

    def subscribe_events(self) -> Iterator[EventRecord]: ...

    def snapshot(self, channel: int) -> OperationResult: ...

    def list_recordings(self, query: dict) -> OperationResult: ...

    def playback(self, reference: str) -> OperationResult: ...

    def prepare_action(self, action: str, parameters: dict) -> ActionProposal | OperationResult: ...

    def execute_action(self, proposal_id: str) -> OperationResult: ...
