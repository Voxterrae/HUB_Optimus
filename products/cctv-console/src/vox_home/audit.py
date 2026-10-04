"""Bounded local JSONL audit with fixed fields and no arbitrary payload values.

Only the trusted core calls this sink. A successful execution may include a
small allowlisted state summary; denied requests and reads never record state.
No log rotation or background work: the caller handles a full/unwritable sink
before admitting a mutating action. Local directory ACLs are deployment work.
"""

import json
import math
import os
from pathlib import Path
import stat
from threading import RLock
import time

from .access import AccessContext
from .contracts import ContractValidationError, PERMISSION_OPERATIONS, _identifier


MAX_AUDIT_BYTES = 1024 * 1024
_OUTCOMES = ("success", "denied", "failed", "unsupported")
_STATUSES = ("verified", "advertised", "pending", "unsupported", "success", "failed")
_NUMBER_FIELDS = ("count", "channel", "checked_at", "expires_at")
_BOOLEAN_FIELDS = ("enabled", "revoked")
_LOCK = RLock()


class AuditLimitError(OSError):
    """The bounded audit sink is full; no append was performed."""


def _safe_state(state: dict | None) -> dict | None:
    if state is None:
        return None
    if type(state) is not dict:
        raise ContractValidationError("invalid_type", "audit_state")
    result = {}
    # Fixed lookups bound work even when the caller supplies a large mapping.
    for field in _BOOLEAN_FIELDS:
        value = state.get(field)
        if type(value) is bool:
            result[field] = value
    status = state.get("status")
    if type(status) is str and status in _STATUSES:
        result["status"] = status
    for field in _NUMBER_FIELDS:
        value = state.get(field)
        if type(value) not in (int, float):
            continue
        # Compare before isfinite so huge integers never overflow conversion.
        if not 0 <= value <= 10**12 or not math.isfinite(value):
            continue
        if field in ("count", "channel") and type(value) is not int:
            continue
        if field == "channel" and value < 1:
            continue
        result[field] = value
    return result


class AuditLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def append(self, context: AccessContext, device_id: str, operation: str,
               outcome: str, before: dict | None, after: dict | None) -> None:
        if type(context) is not AccessContext:
            raise ContractValidationError("invalid_type", "context")
        _identifier(device_id, "device_id")
        if type(operation) is not str or operation not in PERMISSION_OPERATIONS:
            raise ContractValidationError("unknown_operation", "operation")
        if type(outcome) is not str or outcome not in _OUTCOMES:
            raise ContractValidationError("invalid_value", "outcome")
        record = {
            "at": time.time(), "site_id": context.site_id,
            "principal_id": context.principal_id, "grant_id": context.grant_id,
            "device_id": device_id, "operation": operation, "outcome": outcome,
            "before": None, "after": None,
        }
        if operation == "execute_action" and outcome == "success":
            record["before"] = _safe_state(before)
            record["after"] = _safe_state(after)
        data = (json.dumps(record, ensure_ascii=True, allow_nan=False,
                           separators=(",", ":")) + "\n").encode("ascii")
        # The fixed schema and bounded identifiers produce a small record.
        if len(data) > 4096:
            raise AuditLimitError("audit_record_too_large")
        with _LOCK:
            # Refuse symlink sinks. On systems without O_NOFOLLOW the trusted
            # directory ACL must also prevent malicious path replacement.
            if self.path.is_symlink():
                raise OSError("unsafe_audit_sink")
            flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
            flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            descriptor = os.open(self.path, flags, 0o600)
            try:
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise OSError("unsafe_audit_sink")
                if info.st_size + len(data) > MAX_AUDIT_BYTES:
                    raise AuditLimitError("audit_full")
                view = memoryview(data)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise OSError("audit_write_failed")
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
