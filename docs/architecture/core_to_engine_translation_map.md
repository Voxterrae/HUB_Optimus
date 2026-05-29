# Core-to-Engine Translation Map

## Status

Scoped architecture document for the first production-aligned step toward a HUB_Optimus Semantic Engine.

This document does not implement runtime behavior, API endpoints, HERMES PWA, AWS deployment, S3 persistence, vector search, dashboards, or model-based judging.

## Decision

HUB_Optimus Core remains the canonical source of truth in GitHub.

The HUB_Optimus Semantic Engine is the executable translation of that core logic into contracts, normalizers, evaluators, scoring policies, audit logs, and decision traces.

HERMES is the future PWA interface that operates the Semantic Engine. HERMES does not replace HUB_Optimus Core.

AWS is the execution container for the Semantic Engine, API, CLI, scripts, and HERMES. AWS does not define semantic authority.

S3 is the future intelligence archive for inputs, evidence, outputs, audit logs, decision traces, and derived datasets. S3 is not the source of truth.

## Why this document exists

The production goal is not to build a generic application. The goal is to translate the versioned logic of HUB_Optimus Core into an executable semantic technology engine.

This map prevents the first implementation step from drifting into UI, cloud infrastructure, dashboards, or model-first judging before the core logic has been translated into explicit engine modules.

## Fixed architecture

```text
GitHub / HUB_Optimus Core
  ↓ core logic translated into executable modules
HUB_Optimus Semantic Engine
  ↓
API / CLI / Scripts
  ↓
HERMES PWA
  ↓
AWS Runtime Container
  ↓
S3 Intelligence Archive
```

## Canonical definitions

### HUB_Optimus Core

The versioned source of truth in GitHub. It includes governance, source-of-truth rules, runtime contracts, documentation, scenarios, benchmarks, and the conceptual separation between claim, evidence, inference, uncertainty, narrative, and operational signal.

### HUB_Optimus Semantic Engine

The executable translation of HUB_Optimus Core. It must implement contracts, normalizers, evaluators, scoring policies, audit logs, and decision traces derived from the core.

The engine must not invent a parallel logic or bypass GitHub as source of truth.

### HERMES PWA

The future power-by PWA interface for operating the Semantic Engine. HERMES may create cases, submit claims and evidence, execute analyses, display contractual results, and expose audit trails.

HERMES must not define semantic authority, scoring logic, evidence rules, or core contracts.

### AWS Runtime Container

The execution environment where the Semantic Engine, API, CLI, scripts, and HERMES may run.

AWS may accelerate development and deployment, but it must not define semantic architecture.

### S3 Intelligence Archive

The future storage layer for original inputs, evidence, analysis results, audit logs, decision traces, and derived datasets.

S3 enables later intelligence work, replay, comparison, and dataset creation. It is not the canonical source of truth.

## Core-to-engine translation table

| Core source | Logic captured | Engine translation | Target module | Priority |
|---|---|---|---|---|
| `README.md` | Separation of reality, evidence, inference, narrative, and operational signal | Structured result sections and decomposition fields | `semantic_engine/core/analysis_result.py` | P0 |
| `docs/context/STATUS.md` | Canonical source hierarchy and language status | Core reference metadata and source provenance | `semantic_engine/core/core_reference.py` | P0 |
| `docs/architecture/runtime_contract.md` | Existing runtime boundary and deterministic output expectations | Engine execution boundary and stable serializer rules | `semantic_engine/contracts/` and `semantic_engine/output/` | P0 |
| `scenario.schema.json` | Current scenario contract | Initial contract translation pattern | `semantic_engine/contracts/scenario.py` | P1 |
| `run_scenario.py` | Current CLI execution discipline | Future engine CLI pattern, without replacing current runner | `semantic_engine/cli/main.py` | P1 |
| `hub_optimus_simulator.py` | Existing kernel execution behavior | Legacy adapter boundary if needed | `semantic_engine/adapters/simulator_adapter.py` | P2 |
| `KERNEL_CHARTER.md` | Non-negotiable stability, integrity, and audit principles | Governance rules and forbidden behaviors | `semantic_engine/governance/` | P0 |
| `TECHNICAL_MANIFESTO.md` | Layered system direction | Engine module boundaries and layer separation | `semantic_engine/` | P1 |
| `INTEGRITY_SCORING_SYSTEM.md` | Planned integrity-scoring dimensions | Declared scoring dimensions, not complex scoring yet | `semantic_engine/evaluators/integrity_dimensions.py` | P2 |
| `v1_core/workflow/04_scenario_template.md` | Human scenario structuring pattern | Input normalization guidance | `semantic_engine/normalizers/scenario_normalizer.py` | P1 |
| `v1_core/workflow/05_meta_learning.md` | Learning from failures and iteration | Audit and meta-learning trace records | `semantic_engine/audit/meta_learning.py` | P2 |
| Issues and PRs | Operational source of truth for active work | Traceable development gates | GitHub issue/PR workflow | P0 |

## Minimal Semantic Engine modules

The first executable engine should be built from these modules only after this map is merged.

```text
semantic_engine/
  core/
  contracts/
  normalizers/
  evaluators/
  scoring/
  governance/
  audit/
  cli/
```

### `core/`

Owns internal domain records such as claim records, evidence records, analysis results, and core references.

### `contracts/`

Owns versioned input and output contracts. Initial contracts should include `CaseInput`, `EvidenceItem`, `AnalysisResult`, `AuditLogEntry`, and `DecisionTrace`.

### `normalizers/`

Transforms raw text, claims, evidence, files, or scenario-like inputs into stable engine objects. Normalizers do not decide truth.

### `evaluators/`

Applies structural checks derived from the core logic: ambiguity, evidence completeness, inference separation, uncertainty, narrative amplification, contradiction, and operational relevance.

### `scoring/`

Computes explicit and explainable risk, confidence, and severity values after evaluators emit structured signals.

Scoring must not be model-only or hidden in UI/API code.

### `governance/`

Encodes source-of-truth rules, forbidden behaviors, authority boundaries, and escalation requirements.

### `audit/`

Records every relevant transformation, rule application, evaluator result, uncertainty, and output decision.

### `cli/`

Provides the first executable entry point for local and AWS runtime execution before API and HERMES exist.

## Translation order

The engine should be implemented in this order:

1. `AnalysisResult`
2. `ClaimRecord`
3. `EvidenceRecord`
4. `DecisionTrace`
5. `AuditLogEntry`
6. CLI execution later
7. S3 persistence after CLI outputs are stable
8. API after the CLI proves the engine contract
9. HERMES PWA after the API contract exists
10. Vector search only after enough structured history exists

## Out of scope for this document

- HERMES implementation
- AWS deployment
- S3 persistence
- API endpoints
- CLI implementation
- Vector database
- Dashboards
- LLM-as-judge
- SLM-as-judge
- Complex semantic scoring
- Authentication
- Multi-user workflows
- Workers or queues
- Changes to `run_scenario.py`
- Changes to `hub_optimus_simulator.py`
- Changes to `scenario.schema.json`
- Changes to CI workflows

## Acceptance criteria

This document is acceptable when:

- It identifies the production goal as translating HUB_Optimus Core into a Semantic Engine.
- It distinguishes Core, Semantic Engine, HERMES, AWS, and S3.
- It maps existing GitHub sources to future engine modules.
- It states what must not be implemented in this first step.
- It keeps the existing runtime untouched.
- It provides a gate for moving to minimal engine contracts.

## Validation

For a documentation-only PR touching this file, use:

```bash
git diff --check
python tools/check_mojibake.py docs v1_core
```

If the local environment supports the full test suite, also run:

```bash
pytest
```

## Gate to Hito 2: Engine contracts

Only move to minimal engine contracts after this document is merged into `main`.

Hito 2 may begin when:

- this map exists in `main`;
- no runtime behavior was changed;
- Core authority remains in GitHub;
- HERMES remains an interface, not the system center;
- AWS remains execution infrastructure, not semantic architecture;
- S3 remains an archive, not source of truth;
- the next PR can focus only on contracts.
