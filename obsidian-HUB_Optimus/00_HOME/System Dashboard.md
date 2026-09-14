---
type: "dashboard"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "dashboard"
  - "status"
  - "project-intelligence"
---

# System Dashboard

## Baseline

| Field | Value |
| --- | --- |
| Repository | `Voxterrae/HUB_Optimus` |
| Branch | `main` |
| Commit | `30e985226347b4bc59b0e187b96633a09647ca42` |
| Tree | `fabb9da1fdb6979df0bc764017752f118088e69f` |
| Analysis date | `2026-08-21` |
| Components | 16 |
| Interfaces | 7 |
| Entities | 13 |
| Relations | 25 |
| Risks | 8 |

## Project

HUB_Optimus combina [[Canonical v1 Methodology]], [[Governance Guardrails]], prototipos ejecutables, datasets, operaciones y documentación. Ninguna nota de este vault amplía el comportamiento real.

## Component Scorecard

| Component | Status | Layer | Evidence |
| --- | --- | --- | --- |
| [[Governance Guardrails]] | `active` | governance | CONFIRMED |
| [[Canonical v1 Methodology]] | `active` | methodology | CONFIRMED |
| [[Scenario Contract and Loader]] | `active` | backend | CONFIRMED |
| [[Round-based Simulator]] | `active` | backend | CONFIRMED |
| [[Semantic Engine Contracts and CLI]] | `partial` | backend | CONFIRMED |
| [[Operator PWA]] | `partial` | frontend | CONFIRMED |
| [[Operator Learning Store]] | `partial` | data | CONFIRMED |
| [[Controlled URL Intake]] | `partial` | integration | CONFIRMED |
| [[Local HTTP API]] | `partial` | backend | CONFIRMED |
| [[EC2 Core Runner and Run Registry]] | `partial` | operations | CONFIRMED |
| [[EC2 Release Operations]] | `partial` | infrastructure | CONFIRMED |
| [[Public Static Site]] | `active` | frontend | CONFIRMED |
| [[GitHub Pages Pipeline]] | `active` | deployment | CONFIRMED |
| [[Scenario Laboratory and Datasets]] | `experimental` | research | CONFIRMED |
| [[Tests and Quality Gates]] | `active` | testing | CONFIRMED |
| [[Local Control Prototype]] | `experimental` | experimental | CONFIRMED |

## APIs and Commands

- HTTP local: [[GET health]], [[GET status]], [[POST intake url]], [[POST analyze]].
- CLI: [[Scenario CLI]], [[Semantic Engine CLI]], [[hub-core CLI]].
- Catálogo completo: [[Interface Catalogue]].

## Data

- [[Scenario Data Model]]
- [[Semantic Data Model]]
- [[Operator Learning Data]]
- [[Operational Records]]

## Tests

El gate principal es `python -m pytest -q`, acompañado por encoding, narrative consistency, action pins y tooling PowerShell. Véase [[Testing Strategy]].

## Deployment

| Target | Source status | Runtime state |
| --- | --- | --- |
| GitHub Pages | `active` | `unknown` hasta verificar una ejecución |
| Managed Linux/EC2 | `partial` | `unknown` |
| Nginx public allowlist | `partial` | `unknown` |

## Risks

| Risk | Severity | Status | Primary mitigation |
| --- | --- | --- | --- |
| Documentation drift | `high` | `active` | Fijar cada análisis a commit/tree y favorecer código, schemas, tests y workflows actuales. |
| Ambition–implementation gap | `high` | `active` | Mostrar límites por componente y evitar claims de truth/prediction/autonomy. |
| External deployment state | `high` | `unknown` | Verificar el objeto externo tras cada despliegue y registrar commit/receipts. |
| Draft mistaken for evidence | `high` | `active` | Conservar provenance, uncertainty, verification_status y aprobación humana. |
| API exposure boundary | `high` | `partial` | Mantener loopback, allowlist mínima y no exponer /analyze o /status sin un diseño autenticado separado. |
| Methodology/runtime conflation | `medium` | `active` | Representar la relación como guía humana, no como call path. |
| Project intelligence staleness | `medium` | `active` | Aplicar el protocolo delta, actualizar commit/tree y validar model/notes/site en un PR acotado. |
| Single owner review dependency | `medium` | `active` | Mantener PRs pequeños, evidencia clara y no eludir la puerta de propietario. |

## Repository Commit

Toda afirmación técnica se refiere a `30e985226347b4bc59b0e187b96633a09647ca42`. Para actualizar el snapshot, seguir [[Update Protocol]].
