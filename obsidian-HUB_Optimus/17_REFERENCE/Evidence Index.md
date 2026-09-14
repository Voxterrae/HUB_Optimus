---
type: "evidence-index"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "evidence"
  - "source-of-truth"
  - "reference"
---

# Evidence Index

## Repository and Governance

- `AGENTS.md`
- `docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md`
- `config/governance/owner_identity.v1.json`
- `docs/context/SOURCE_OF_TRUTH.md`
- `docs/context/OWNER_AUTHORITY_HANDOFF.md`
- `.github/CODEOWNERS`

## Architecture and Status

- `docs/architecture/system_architecture_map.md`
- `docs/architecture/runtime_contract.md`
- `docs/architecture/capability_status.md`
- `docs/context/PROJECT_OVERVIEW.md`
- `docs/context/STATUS.md`

## Runtime Evidence

- `scenario.schema.json`
- `run_scenario.py`
- `hub_optimus_simulator.py`
- `semantic_engine/contracts/`
- `semantic_engine/cli/`
- `ops/ec2/hub-api.sh`
- `ops/ec2/hub-core.sh`

## Frontend Evidence

- `site/index.html`
- `site/styles.css`
- `site/operator/`
- `.github/workflows/pages.yml`

## Operations Evidence

- `ops/ec2/README.md`
- `ops/ec2/deploy-current.sh`
- `ops/ec2/rollback-current.sh`
- `ops/ec2/preflight-deploy.sh`
- `ops/ec2/nginx/operator-api.conf`

## Test Evidence

- `.github/workflows/ci.yml`
- `tests/`
- `benchmarks/expected/`

## Documentation Drift

### Derived capability snapshot

**Documentation states:** `capability_status.md` and `PROJECT_OVERVIEW.md` were verified against `df0ef345e5ac627f3e2735573c802fe2f60821f4` on 2026-07-29.

**Code currently shows:** `main` is `30e985226347b4bc59b0e187b96633a09647ca42` with tree `fabb9da1fdb6979df0bc764017752f118088e69f`.

**Likely current truth:** use current code/config/schema/tests for behavior, retaining those documents as historical derived views.

**Evidence:** current commit, current tree, and the pinned headers of the older documents.

### Operator URL intake

**Documentation states:** architecture/contracts define controlled intake and a compatible handoff.

**Code currently shows:** the public Operator remains local/manual and does not prove an available public backend.

**Likely current truth:** backend is separately controlled/local; deployment is `UNKNOWN`.

**Evidence:** `site/operator/index.html`, `ops/ec2/hub-api.sh`, Nginx source and commit `c399c94e098058a723482001811c7d8491ebbd5e`.

## Explicit Non-capabilities

- Autonomous truth adjudication or motive inference
- Prediction or probabilistic forecasting of real-world outcomes
- Full automatic execution of the canonical v1 methodology
- Public authenticated Semantic Engine service
- HERMES production application
- Post-quantum control plane
- Enterprise billing, authentication or customer tenancy
- Proof of current Pages, EC2, DNS, TLS, Nginx or repository-settings state
- AI ownership, self-ratification or autonomous merge authority

## Evidence Rule

A source path is evidence only for what its content establishes. A green unrelated test, merged RFC or file presence cannot be generalized into a broader claim.
