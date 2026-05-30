"""Core record contracts for the HUB_Optimus Semantic Engine.

These dataclasses intentionally stay small and stdlib-only. They define the
first executable shape for claims and evidence without adding evaluators,
scoring, API, HERMES, AWS, S3, vector search, or model-judge behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ClaimRecord:
    """A structured claim extracted or submitted for analysis."""

    claim_id: str
    text: str
    source_ref: str
    claim_type: str = "unknown"
    requires_evidence: bool = True
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "source_ref": self.source_ref,
            "claim_type": self.claim_type,
            "requires_evidence": self.requires_evidence,
            "status": self.status,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class EvidenceRecord:
    """A structured evidence item linked to one or more claims."""

    evidence_id: str
    text: str
    source_ref: str
    source_type: str = "unknown"
    supports_claim_ids: tuple[str, ...] = ()
    contradicts_claim_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "text": self.text,
            "source_ref": self.source_ref,
            "source_type": self.source_type,
            "supports_claim_ids": list(self.supports_claim_ids),
            "contradicts_claim_ids": list(self.contradicts_claim_ids),
            "limitations": list(self.limitations),
            "metadata": dict(self.metadata),
        }
