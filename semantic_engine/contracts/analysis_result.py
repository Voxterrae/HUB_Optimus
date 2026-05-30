"""Analysis result contract for the HUB_Optimus Semantic Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .audit_log import AuditLogEntry
from .decision_trace import DecisionTrace
from .records import ClaimRecord, EvidenceRecord


@dataclass(frozen=True)
class AnalysisResult:
    """The minimal structured output of a Semantic Engine analysis.

    This contract separates claims, evidence, inferences, uncertainties,
    narrative amplification, and operational signal. It does not perform
    evaluation or scoring by itself.
    """

    case_id: str
    core_version_ref: str
    input_summary: str
    claims: tuple[ClaimRecord, ...] = ()
    evidence: tuple[EvidenceRecord, ...] = ()
    inferences: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    narrative_amplification: tuple[str, ...] = ()
    operational_signal: str = "none"
    status: str = "draft"
    decision_trace: tuple[DecisionTrace, ...] = ()
    audit_log: tuple[AuditLogEntry, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "core_version_ref": self.core_version_ref,
            "input_summary": self.input_summary,
            "claims": [claim.to_dict() for claim in self.claims],
            "evidence": [item.to_dict() for item in self.evidence],
            "inferences": list(self.inferences),
            "uncertainties": list(self.uncertainties),
            "narrative_amplification": list(self.narrative_amplification),
            "operational_signal": self.operational_signal,
            "status": self.status,
            "decision_trace": [entry.to_dict() for entry in self.decision_trace],
            "audit_log": [entry.to_dict() for entry in self.audit_log],
            "metadata": dict(self.metadata),
        }
