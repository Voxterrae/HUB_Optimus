"""Audit log contract for Semantic Engine runs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp with second precision."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def copy_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a deep copy of an audit snapshot if one exists."""

    if snapshot is None:
        return None
    return deepcopy(snapshot)


@dataclass(frozen=True)
class AuditLogEntry:
    """A durable audit event for a Semantic Engine action."""

    event_id: str
    action: str
    object_type: str
    object_id: str
    reason: str
    timestamp: str = field(default_factory=utc_now_iso)
    operator: str = "system"
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "operator": self.operator,
            "action": self.action,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "before": copy_snapshot(self.before),
            "after": copy_snapshot(self.after),
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }
