---
type: "data-model"
status: "partial"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "semantic_engine/contracts/"
tags:
  - "data"
  - "semantic-engine"
  - "contracts"
---

# Semantic Data Model

## CaseInput v1

Required:

- `case_id`
- `core_version_ref`
- `input_summary`

Optional collections and fields:

- `claims`
- `evidence`
- `inferences`
- `uncertainties`
- `narrative_amplification`
- `operational_signal`
- `status`
- `metadata`

Unknown fields are rejected except inside explicit `metadata`, which remains opaque and non-authoritative.

## ClaimRecord

- `claim_id`, `text`, `source_ref`
- optional `claim_type`, `requires_evidence`, `status`, `metadata`

## EvidenceRecord

- `evidence_id`, `text`, `source_ref`
- optional `source_type`, supports/contradicts claim IDs, limitations, metadata

## Cross-record Integrity

- Claim IDs are unique.
- Evidence IDs are unique.
- Every supports/contradicts reference names a submitted claim.
- Input cannot inject output-only decision/audit fields.

## AnalysisResult

```text
case identity
claims
evidence
inferences
uncertainties
narrative amplification
operational signal
status
decision trace
audit log
metadata
```

El CLI mínimo conserva la información enviada y deja decision trace/audit log vacíos salvo que otra capa explícita los construya.

## Relationships

```mermaid
erDiagram
    CASE_INPUT ||--o{ CLAIM_RECORD : contains
    CASE_INPUT ||--o{ EVIDENCE_RECORD : contains
    EVIDENCE_RECORD }o--o{ CLAIM_RECORD : references
    CASE_INPUT ||--|| ANALYSIS_RESULT : produces
    ANALYSIS_RESULT ||--o{ DECISION_TRACE : may_contain
    ANALYSIS_RESULT ||--o{ AUDIT_LOG_ENTRY : may_contain
```

## Related

- [[Semantic Engine Contracts and CLI]]
- [[Semantic Engine CLI]]
- [[POST analyze]]
