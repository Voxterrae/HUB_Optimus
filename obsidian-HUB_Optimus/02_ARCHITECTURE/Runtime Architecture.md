---
type: "runtime-architecture"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "architecture"
  - "runtime"
---

# Runtime Architecture

## Scenario Runtime

```mermaid
sequenceDiagram
    participant U as User/Tool
    participant L as run_scenario loader
    participant S as scenario.schema.json
    participant M as Simulator
    U->>L: Scenario JSON
    L->>S: Draft 2020-12 validation
    L->>L: unique actor identity checks
    L->>M: Scenario object
    M->>M: isolated seeded rounds
    M-->>U: SimulationResult JSON
```

Boundary: exact-match success in any actor action; no full methodology execution.

## Semantic Runtime

```mermaid
sequenceDiagram
    participant C as Client
    participant V as CaseInput validator
    participant CLI as Semantic Engine CLI
    participant R as AnalysisResult
    C->>V: CaseInput JSON
    V->>V: schema + unique IDs + reference integrity
    V->>CLI: validated payload
    CLI->>R: deterministic record assembly
    R-->>C: strict JSON
```

Boundary: no scoring, truth verdict or model judge.

## Local Analyze Runtime

```mermaid
sequenceDiagram
    participant C as Local client
    participant API as Local HTTP API
    participant F as 0600 tempfile
    participant Core as hub-core
    participant CLI as Semantic CLI
    participant Runs as run directory
    C->>API: POST /analyze
    API->>F: strict CaseInput
    API->>Core: analyze file
    Core->>Runs: RUN_STATE
    Core->>CLI: analyze copied input
    CLI->>Runs: analysis_result.json
    API->>F: delete
    API-->>C: exact run_id + result
```

## Controlled Intake Runtime

URL → URI/DNS/IP validation → pinned connection → bounded response → HTML/text extraction → unreviewed record.

## Browser Runtime

El public site y Operator son estáticos. Operator mantiene trabajo local y puede preparar contratos; la disponibilidad de un backend público no se infiere.

## Related

- [[Scenario CLI]]
- [[Semantic Engine CLI]]
- [[Interface Catalogue]]
- [[Operational Records]]
