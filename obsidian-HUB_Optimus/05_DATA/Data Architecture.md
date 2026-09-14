---
type: "data-architecture"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "data"
  - "architecture"
  - "contracts"
---

# Data Architecture

## Data Model

| Entity | Status | Purpose | Source |
| --- | --- | --- | --- |
| Scenario | `active` | Contrato de contexto, roles, criterios y rondas. | `scenario.schema.json`, `hub_optimus_simulator.py` |
| ActorRole | `active` | Nombre único y tipo de rol dentro de un escenario. | `scenario.schema.json`, `run_scenario.py` |
| SimulationResult | `active` | Estado, rounds, history y detail de una ejecución. | `hub_optimus_simulator.py` |
| CaseInput v1 | `partial` | Contrato de entrada para Semantic Engine. | `semantic_engine/contracts/case_input.schema.json`, `semantic_engine/contracts/case_input.py` |
| ClaimRecord | `partial` | Afirmación estructurada con source_ref y estado. | `semantic_engine/contracts/records.py` |
| EvidenceRecord | `partial` | Evidencia estructurada que apoya o contradice claims. | `semantic_engine/contracts/records.py` |
| AnalysisResult | `partial` | Salida contractual que separa claims, evidence, inferences, uncertainties y signal. | `semantic_engine/contracts/analysis_result.py` |
| DecisionTrace | `partial` | Transformación o regla trazable; el CLI mínimo no la rellena automáticamente. | `semantic_engine/contracts/decision_trace.py` |
| AuditLogEntry | `partial` | Contrato de evento de auditoría con snapshots. | `semantic_engine/contracts/audit_log.py` |
| Operator Learning Candidate v1 | `partial` | Grafo local no canónico con nodes, relations, metrics, closure e history. | `site/operator/schemas/operator_learning_candidate.v1.schema.json` |
| Controlled URL Intake Record | `partial` | Texto recuperado con procedencia, límites y estado unreviewed. | `ops/ec2/controlled_url_intake.v1.schema.json` |
| RUN_STATE | `partial` | Identidad de run, command, release, commit, path, input y timestamp. | `ops/ec2/hub-core.sh` |
| RELEASE_STATE / ROLLBACK_STATE | `partial` | Provenance de release, launcher, validación y rollback. | `ops/ec2/deploy-current.sh`, `ops/ec2/rollback-current.sh` |

## Persistence Modes

| Store | Data | Persistence | Authority |
| --- | --- | --- | --- |
| Scenario/result files | Scenario and SimulationResult | Local filesystem | Synthetic runtime artifact |
| Semantic output files | CaseInput and AnalysisResult | Local file or run directory | Structured review record |
| Operator IndexedDB | Learning candidates | Browser local storage | Local non-canonical |
| Host run registry | RUN_STATE, logs, results | `/opt/hub-optimus/shared/runs` | Operational provenance |
| Release records | RELEASE_STATE/ROLLBACK_STATE | Managed host filesystem | Operational provenance |
| Repository | Schemas, fixtures, datasets | Git history | Versioned source at commit |
| External deployment state | Pages/EC2/DNS/settings | External systems | `UNKNOWN` until inspected |

## Data Ownership

- Humans own assertions, source selection, review and approval.
- Runtime outputs own no truth authority.
- Learning candidates remain local and non-canonical.
- Governance records require accountable human action.
- External systems are authoritative only for their own current state.

## Data Flow

Abrir [[Architecture Data Flow]].

## Validation

- Scenario: JSON Schema + actor uniqueness.
- CaseInput: JSON Schema + record ID uniqueness + evidence references.
- Intake: URI/network/size/content bounds + response schema.
- Learning: JSON Schema/model invariants + hashes + append-only state transitions.
- Run/release: explicit commit, path, run ID and launcher provenance.

## Related

- [[Scenario Data Model]]
- [[Semantic Data Model]]
- [[Operator Learning Data]]
- [[Operational Records]]
- [[Security Boundaries]]
