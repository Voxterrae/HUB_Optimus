---
type: "source-map"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "source-map"
  - "code"
  - "architecture"
---

# Source Map

> Conceptual system → source paths. Paths are fixed to repository baseline `30e985226347b4bc59b0e187b96633a09647ca42` by [[Repository Analysis]].

## Governance Guardrails

**Concept:** [[Governance Guardrails]]

**Source**

- `docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md`
- `config/governance/owner_identity.v1.json`
- `docs/context/SOURCE_OF_TRUTH.md`
- `docs/context/OWNER_AUTHORITY_HANDOFF.md`
- `.github/CODEOWNERS`

**Used by / related**

- No supported runtime dependency; see component boundary.

**Status:** `active` · **Evidence:** `CONFIRMED`

## Canonical v1 Methodology

**Concept:** [[Canonical v1 Methodology]]

**Source**

- `docs/context/STATUS.md`
- `v1_core/languages/es/01_base_declaracion.md`
- `v1_core/languages/es/02_arquitectura_base.md`
- `v1_core/languages/es/03_flujo_operativo.md`
- `v1_core/workflow/README.md`

**Used by / related**

- [[Round-based Simulator]]

**Status:** `active` · **Evidence:** `CONFIRMED`

## Scenario Contract and Loader

**Concept:** [[Scenario Contract and Loader]]

**Source**

- `scenario.schema.json`
- `run_scenario.py`

**Used by / related**

- [[Scenario Laboratory and Datasets]]
- [[Round-based Simulator]]

**Status:** `active` · **Evidence:** `CONFIRMED`

## Round-based Simulator

**Concept:** [[Round-based Simulator]]

**Source**

- `hub_optimus_simulator.py`
- `benchmarks/run_benchmarks.py`

**Used by / related**

- [[Canonical v1 Methodology]]
- [[Scenario Contract and Loader]]

**Status:** `active` · **Evidence:** `CONFIRMED`

## Semantic Engine Contracts and CLI

**Concept:** [[Semantic Engine Contracts and CLI]]

**Source**

- `semantic_engine/contracts/case_input.schema.json`
- `semantic_engine/contracts/case_input.py`
- `semantic_engine/contracts/analysis_result.py`
- `semantic_engine/cli/__main__.py`

**Used by / related**

- [[EC2 Core Runner and Run Registry]]
- [[Operator PWA]]

**Status:** `partial` · **Evidence:** `CONFIRMED`

## Operator PWA

**Concept:** [[Operator PWA]]

**Source**

- `site/operator/index.html`
- `site/operator/sw.js`
- `site/operator/learning-candidate.v1.js`
- `site/operator/learning-store.v1.js`

**Used by / related**

- [[Operator Learning Store]]
- [[Public Static Site]]
- [[Semantic Engine Contracts and CLI]]

**Status:** `partial` · **Evidence:** `CONFIRMED`

## Operator Learning Store

**Concept:** [[Operator Learning Store]]

**Source**

- `site/operator/learning-store.v1.js`
- `site/operator/learning-candidate.v1.js`
- `site/operator/schemas/operator_learning_candidate.v1.schema.json`

**Used by / related**

- [[Operator PWA]]

**Status:** `partial` · **Evidence:** `CONFIRMED`

## Controlled URL Intake

**Concept:** [[Controlled URL Intake]]

**Source**

- `ops/ec2/hub-api.sh`
- `ops/ec2/controlled_url_intake.v1.schema.json`
- `ops/ec2/nginx/operator-api.conf`

**Used by / related**

- [[Local HTTP API]]

**Status:** `partial` · **Evidence:** `CONFIRMED`

## Local HTTP API

**Concept:** [[Local HTTP API]]

**Source**

- `ops/ec2/hub-api.sh`
- `ops/ec2/hub-api.service`
- `ops/ec2/hub-api-control.sh`

**Used by / related**

- [[Local Control Prototype]]
- [[Controlled URL Intake]]
- [[EC2 Core Runner and Run Registry]]

**Status:** `partial` · **Evidence:** `CONFIRMED`

## EC2 Core Runner and Run Registry

**Concept:** [[EC2 Core Runner and Run Registry]]

**Source**

- `ops/ec2/hub-core.sh`
- `ops/ec2/hub-runs.sh`
- `ops/ec2/README.md`

**Used by / related**

- [[Local HTTP API]]
- [[Semantic Engine Contracts and CLI]]

**Status:** `partial` · **Evidence:** `CONFIRMED`

## EC2 Release Operations

**Concept:** [[EC2 Release Operations]]

**Source**

- `ops/ec2/deploy-current.sh`
- `ops/ec2/rollback-current.sh`
- `ops/ec2/preflight-deploy.sh`
- `ops/ec2/README.md`

**Used by / related**

- No supported runtime dependency; see component boundary.

**Status:** `partial` · **Evidence:** `CONFIRMED`

## Public Static Site

**Concept:** [[Public Static Site]]

**Source**

- `site/index.html`
- `site/styles.css`
- `site/app.js`
- `site/globe.js`

**Used by / related**

- [[Operator PWA]]

**Status:** `active` · **Evidence:** `CONFIRMED`

## GitHub Pages Pipeline

**Concept:** [[GitHub Pages Pipeline]]

**Source**

- `.github/workflows/pages.yml`

**Used by / related**

- No supported runtime dependency; see component boundary.

**Status:** `active` · **Evidence:** `CONFIRMED`

## Scenario Laboratory and Datasets

**Concept:** [[Scenario Laboratory and Datasets]]

**Source**

- `tools/scenario_generator/`
- `tools/scenario_mutator.py`
- `tools/scenario_telemetry.py`
- `benchmarks/`

**Used by / related**

- [[Scenario Contract and Loader]]

**Status:** `experimental` · **Evidence:** `CONFIRMED`

## Tests and Quality Gates

**Concept:** [[Tests and Quality Gates]]

**Source**

- `.github/workflows/ci.yml`
- `tests/`
- `tools/check_mojibake.py`

**Used by / related**

- No supported runtime dependency; see component boundary.

**Status:** `active` · **Evidence:** `CONFIRMED`

## Local Control Prototype

**Concept:** [[Local Control Prototype]]

**Source**

- `hub_optimus/hub_optimus_control.py`

**Used by / related**

- [[Local HTTP API]]

**Status:** `experimental` · **Evidence:** `CONFIRMED`


## Interface Sources

- [[GET health]] → `ops/ec2/hub-api.sh`, `ops/ec2/nginx/operator-api.conf`
- [[GET status]] → `ops/ec2/hub-api.sh`
- [[POST intake url]] → `ops/ec2/hub-api.sh`, `ops/ec2/controlled_url_intake.v1.schema.json`, `ops/ec2/nginx/operator-api.conf`
- [[POST analyze]] → `ops/ec2/hub-api.sh`, `ops/ec2/hub-core.sh`, `semantic_engine/cli/__main__.py`
- [[Scenario CLI]] → `run_scenario.py`, `scenario.schema.json`
- [[Semantic Engine CLI]] → `semantic_engine/cli/__main__.py`, `semantic_engine/contracts/case_input.py`
- [[hub-core CLI]] → `ops/ec2/hub-core.sh`

## Structured Model

- `site/obsidian-HUB_Optimus/system.json`
- Consumed by `site/obsidian-HUB_Optimus/app.js`
- Documented by this vault
- Validated by `tests/test_project_intelligence_site.py`

## Related

- [[Evidence Index]]
- [[Architecture Map]]
- [[Update Protocol]]
