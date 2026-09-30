---
type: "dependency-graph"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "architecture"
  - "dependencies"
---

# Dependency Graph

## Internal Dependencies

```mermaid
flowchart TB
    Loader["Scenario Contract and Loader"] --> Simulator["Round-based Simulator"]
    Lab["Scenario Laboratory"] --> Loader
    API["Local HTTP API"] --> Intake["Controlled URL Intake"]
    API --> Core["hub-core"]
    Core --> Semantic["Semantic Engine CLI"]
    Core --> Loader
    Operator["Operator PWA"] --> Store["Operator Learning Store"]
    Pages["GitHub Pages Pipeline"] --> Site["Public Static Site"]
    Site --> Operator
    Tests["Tests and Quality Gates"] -. "verifies bounded contracts" .-> Loader
    Tests -.-> Semantic
    Tests -.-> Operator
    Tests -.-> API
```

## External Dependencies

```mermaid
flowchart LR
    Python["Python 3.11+"] --> Jsonschema["jsonschema 4.x"]
    Pytest["pytest 9.x"] --> Tests["Python test suite"]
    Browser["Browser APIs"] --> Site["Static site / Operator"]
    Actions["GitHub Actions"] --> Pages["GitHub Pages"]
    Linux["Linux + git + systemd"] --> Ops["EC2 operations"]
    PowerShell["PowerShell 7"] --> Tooling["PowerShell behavior checks"]
```

## Isolated Prototype

[[Local Control Prototype]] no es una dependencia del Scenario runtime, Semantic Engine, Operator ni operations. Su relación arquitectónica es aislamiento explícito.

## Dependency Policy

- Runtime Python: `requirements.txt`.
- Development/test: `requirements-dev.txt`.
- No `package.json` ni build frontend.
- No framework JavaScript de grafo añadido.
- GitHub Actions están fijadas por SHA y auditadas.

## Related

- [[Dependencies]]
- [[Testing Strategy]]
- [[Infrastructure Boundary]]
