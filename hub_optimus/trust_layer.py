from __future__ import annotations

import re
from typing import Literal

ClaimLevel = Literal["A", "B", "C"]
ClaimType = Literal[
    "verification_mechanism",
    "third_party_audit",
    "metrics_reporting",
    "declarative_only",
]

# Detect phrases like:
# "without verification", "no independent monitoring", "sin verificacion", etc.
_NEGATED_VERIFICATION_RE = re.compile(
    r"\b(no|without|lacking|absent|missing|sin)\b.{0,80}\b("
    r"verification|verificacion|monitoring|monitor|audit|auditor|"
    r"inspection|inspeccion"
    r")\b",
    re.IGNORECASE | re.DOTALL,
)


def detect_claim_type(claim: str) -> ClaimType:
    c = (claim or "").strip().lower()
    if not c:
        return "declarative_only"

    # If claim explicitly states missing verification, never classify as A/B.
    if _NEGATED_VERIFICATION_RE.search(c):
        return "declarative_only"

    third_party_markers = [
        "third-party",
        "third party",
        "independent",
        "un ",
        "u.n.",
        "osce",
        "icrc",
        "iaea",
        "external auditor",
        "international observers",
        "observer mission",
        "tercero independiente",
        "terceros independientes",
        "observadores internacionales",
        "auditoria externa",
    ]
    audit_markers = [
        "audit",
        "auditor",
        "inspection",
        "inspections",
        "monitor",
        "monitoring",
        "verified",
        "verification",
        "inspeccion",
        "verificacion",
    ]
    if any(m in c for m in third_party_markers) and any(m in c for m in audit_markers):
        return "third_party_audit"

    verification_markers = [
        "verification mechanism",
        "verification",
        "monitoring",
        "monitor",
        "inspection",
        "inspections",
        "hotline",
        "observer",
        "observers",
        "sensors",
        "satellite",
        "logs",
        "audit trail",
        "verificacion",
        "inspeccion",
        "observadores",
        "sensores",
        "satelite",
        "registros",
    ]
    if any(m in c for m in verification_markers):
        return "verification_mechanism"

    metrics_markers = [
        "kpi",
        "kpis",
        "metrics",
        "metric",
        "measurable",
        "measure",
        "measured",
        "tracked",
        "reported",
        "reporting",
        "dashboard",
        "weekly report",
        "monthly report",
        "quarterly report",
        "indicadores",
        "metricas",
        "medible",
        "medicion",
        "seguimiento",
        "reportado",
        "informes",
    ]
    if any(m in c for m in metrics_markers):
        return "metrics_reporting"

    return "declarative_only"


def _level_for_type(claim_type: ClaimType) -> ClaimLevel:
    if claim_type == "third_party_audit":
        return "A"
    if claim_type in ("verification_mechanism", "metrics_reporting"):
        return "B"
    return "C"


def classify_claim_typed(claim: str) -> tuple[ClaimLevel, ClaimType]:
    claim_type = detect_claim_type(claim)
    return _level_for_type(claim_type), claim_type


# Backward compatible: keeps old API unchanged.
def classify_claim(claim: str) -> ClaimLevel:
    level, _ = classify_claim_typed(claim)
    return level


def evidence_required(level: ClaimLevel, claim_type: ClaimType | None = None) -> list[str]:
    """
    Backward compatible:
    - evidence_required("A") -> generic by level
    - evidence_required("A", "third_party_audit") -> specific by type + level
    """
    if claim_type is None:
        return _evidence_generic(level)

    templates: dict[tuple[ClaimType, ClaimLevel], list[str]] = {
        ("third_party_audit", "A"): [
            "Mandate / ToR of the independent monitoring body (scope, authority, access).",
            "On-site inspection/observation logs (time-stamped) + incident register.",
            "Public audit/verification reports with methodology + versioned findings.",
            "Chain-of-custody for evidence (incl. imagery/logs) + dispute-resolution protocol.",
        ],
        ("verification_mechanism", "B"): [
            "Defined verification protocol (what is checked, how, cadence, thresholds).",
            "Monitoring data sources (logs/telemetry/field reports) + retention policy.",
            "Access rules + escalation path for violations (hotline, joint commission, triage).",
            "Clear definitions (what counts as a violation) + reporting timeline.",
        ],
        ("metrics_reporting", "B"): [
            "Explicit KPI/metric definitions, baselines, and measurement methodology.",
            "Reporting cadence + publication channel + raw data access policy.",
            "Versioned dataset or audit trail to prevent post-hoc rewriting.",
            "Optional but recommended: independent replication or spot checks.",
        ],
        ("declarative_only", "C"): [
            "Signed agreement text (definitions, scope, parties, timelines).",
            "Operational plan to add verification (mechanism design, access, authority, data).",
            "Incentive-alignment measures (cost of violation, reward of compliance).",
            "Escalation and remediation playbook for breaches.",
        ],
    }

    out = templates.get((claim_type, level))
    if out:
        return out

    return _evidence_generic(level)


def _evidence_generic(level: ClaimLevel) -> list[str]:
    if level == "A":
        return [
            "Independent verification evidence (third-party reports, logs, access protocols).",
            "Time-stamped records sufficient for dispute resolution.",
        ]
    if level == "B":
        return [
            "Measurable commitments with reproducible metrics and transparent reporting.",
            "Audit trail/logs allowing at least partial independent scrutiny.",
        ]
    return [
        "Concrete commitments (definitions + timelines), but insufficient without verification.",
        "Verification/monitoring design required to reduce false-success risk.",
    ]
