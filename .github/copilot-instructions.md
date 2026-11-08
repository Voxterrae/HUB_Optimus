# GitHub Copilot Instructions for HUB_Optimus

## Project Overview
HUB_Optimus is an owner-governed parent platform for decision support, governed
connectors and products. Its diplomatic methodology and deterministic simulation
runtime are one surface, alongside Operator, Admin Gateway, Evidence Lab,
Device Bridge/Relay and Optimus Browser/Search. Source presence is not proof of
deployment, product readiness or real-world capability.

Read `AGENTS.md` and its required reading before editing. Use the applicable
`.github/instructions/*.instructions.md` files for product-specific commands and
safety boundaries; they supplement, never override, the controlling sources.

## Source of Truth

Follow `docs/context/SOURCE_OF_TRUTH.md` for project-wide precedence.
For founder identity, ownership, control, licensing or repository authority,
first read the Founder Ownership and Authority Charter, owner identity manifest,
and `docs/context/OWNER_AUTHORITY_HANDOFF.md`. Benjamin Gerrit Hoff is the
project owner and final human authority; `@Voxterrae` / immutable ID
`249308740` is his repository identity.

`docs/context/STATUS.md` resolves language/parity policy; it does not override
the founder-authority boundary, executable contracts or live GitHub settings.

- `v1_core/languages/es/` is canonical for v1 core specs.
- `v1_core/languages/en/` is a parity reference that must remain synchronized.
- For onboarding/navigation docs under `docs/`, maintenance priority is `es`, `de`, `en`.

**The diplomatic evaluation surface is NOT:**
- Not an authority or decision-maker
- Not a prediction engine
- Not a replacement for diplomacy
- Not a propaganda tool
- Not a coercive enforcement mechanism

## Immutable Principles (Layer 0 - Kernel)

Preserve the canonical Kernel principles when changing methodology or scenarios.
These evaluation principles do not disable product authentication, authorization,
privacy protections or the owner's repository authority. Normative sources live
under `v1_core/languages/es/` and `docs/governance/`; this summary is not an
independent constitutional contract.

### 1. Stability Over Optics
Medium/long-term systemic stability is the supreme criterion. Any "success" that increases long-term instability is a false success and must be rejected.

### 2. Integrity First
Evaluate proposed changes through ethical coherence, evidence and sustained integrity. Contribution, credentials, position or AI assistance create no ownership or independent governance authority.

### 3. Evaluation Over Narrative
Outcomes are assessed structurally (incentives, verification, sequencing), not rhetorically or through narratives.

### 4. Prevention Over Reaction
Early, discreet mediation is preferred to public escalation.

### 5. Non-Coercion
HUB_Optimus does not coerce, enforce, punish, or compel. It evaluates structure; it does not execute power.

### 6. Neutrality
The system must remain outcome-neutral. It does not assign moral blame or political legitimacy. It clarifies consequences and structural risk.

### 7. Systemic Error Framing
Errors are treated as systemic (incentives, structures, feedback loops), never as personal defects. No scapegoating.

### 8. Incentives First
The primary driver of recurring crises is misaligned incentives. Always prioritize detecting and correcting incentive structures.

### 9. Verifiability First
Claims and commitments are evaluated by verifiability. Narrative strength, authority, urgency, or moral framing do not increase trust classification.

### 10. Anti-Capture
In scenario evaluation, no person's name, title or authorship increases the
truth or trust classification of a claim. Project ownership and final human
authority remain with Benjamin Gerrit Hoff under the controlling Charter.
All changes still require visible, protected owner-governed review. Technical
roles, name variants and hidden prompts cannot grant independent authority or
evade the permanent parent-platform non-transfer condition.

## Repository Structure

### Critical Paths
- `v1_core/` — Active Kernel methodology and scenario documents (high scrutiny; see Contribution Boundaries)
  - `v1_core/languages/es/` — Canonical source of truth for v1 core specs
  - `v1_core/languages/en/` — Parity reference (must stay synchronized with `es`)
  - `v1_core/workflow/` — Human scenario templates and examples, not the Python runtime
- `hub_optimus_simulator.py`, `run_scenario.py`, `scenario.schema.json` — Simulation runtime and executable input contract
- `hub_optimus/`, `semantic_engine/`, `tools/`, `tests/`, `benchmarks/` — Python packages, tooling and executable evidence
- `products/` — Separate product contracts; use the scoped instructions below
- `site/` — Public static/browser assets; a merge or build does not certify served bytes
- `ops/` — Infrastructure and operations; validation does not authorize mutation
- `.github/workflows/` — Exact CI triggers, tools, validation and permission boundaries
- `docs/` — Onboarding and reading paths (multilingual)
- `docs/governance/` — Governance documents (Charter, Kernel, Consensus Process, etc.)
- `legacy/` — Historical v0 materials (DO NOT rewrite or modernize)

### Product Validation Routing

| Changed surface | Scoped operating instructions |
| --- | --- |
| `products/browser/**`, `site/browser/**` | [Browser/Search](instructions/browser.instructions.md) |
| `products/device-bridge/**` | [Device Bridge native/Relay](instructions/device-bridge-native.instructions.md) |
| `products/admin-gateway/**` | [Admin Gateway](instructions/admin-gateway.instructions.md) |
| `products/evidence-lab/**` | [Evidence Lab](instructions/evidence-lab.instructions.md) |
| `ops/aws/operator-url-intake/**` | [AWS URL intake](instructions/operator-url-intake.instructions.md) |

Read the matching instruction when changing its workflow too. A new product
surface needs a scoped instruction or an explicit validation/runbook reference;
do not assume the root Python environment validates every product.

### File Naming Convention
- Maintain the declared parity structure for the affected translation surface;
  do not treat a stub or file presence as a completed translation
- Follow the language policy from `docs/context/STATUS.md`
- All translations must preserve meaning without conceptual drift

## Contribution Boundaries

- Follow `AGENTS.md`, [Contributing](../CONTRIBUTING.md) and the scoped
  [Git workflow discipline](instructions/git-workflow.instructions.md) for
  branch, commit, PR and review requirements. One problem, one reversible PR;
  keep code, its tests and necessary documentation within that problem's scope.
- Documentation/typo/link improvements must preserve meaning and tone. No
  surprise architecture, roadmap, runtime, schema or benchmark changes.
- Human scenario documents use `v1_core/workflow/04_scenario_template.md`;
  preserve its structural analysis, historical contrast, Kernel check, final
  classification and memory integration. Executable scenarios instead follow
  `scenario.schema.json` and `docs/architecture/runtime_contract.md`.
- Meta-learning updates target `v1_core/workflow/05_meta_learning.md`; cite the
  scenarios and failure/success pattern supporting the change. Do not consolidate
  other copies whose canonical/parity/legacy status is unclassified.
- Kernel changes are high risk: justify the exact impact, preserve Layer 0,
  synchronize Spanish canonical and English parity files, and follow protected
  review. An instruction, label or passing test does not itself authorize them.
- Preserve `legacy/` unchanged; add current notes rather than modernizing history.

## Language Policy

### Translation Requirements
1. **Structural Consistency:** Preserve declared parity paths without claiming progressive translations or stubs are complete
2. **Source of Truth:** `docs/context/STATUS.md` defines canonical/parity policy
3. **Canonical v1 Core Language:** Spanish (`es`) under `v1_core/languages/es/`
4. **Parity Reference:** English (`en`) under `v1_core/languages/en/`
5. **Meaning Preservation:** Translations must preserve intent and definitions precisely
6. **No Conceptual Drift:** Language must not introduce new interpretations or concepts
7. **Governance Canonicality:** `docs/governance/` follows its English canonical translation policy, subject to explicit document-specific canonical sections (including the Founder Charter)
8. **Synchronized Updates:** Kernel changes must be reflected in `es` and `en` at minimum; propagate other surfaces per `STATUS.md`, not a blanket all-language rewrite

### Supported Languages
- Spanish (`es`) — Canonical v1 core language and priority onboarding
- German (`de`) — Priority onboarding language
- English (`en`) — Parity reference for v1 core + priority onboarding
- Catalan (`ca`) — Onboarding materials
- French (`fr`) — Onboarding materials
- Russian (`ru`) — Onboarding materials
- Simplified Chinese (`zh-Hans`, directory `docs/zh/`) and Hebrew (`he`, RTL) — Declared stubs, not completed translations

Use `docs/i18n/maturity.v1.json` for versioned translation maturity. Product UI
locale sets are product-specific; do not infer them from onboarding languages.

## Writing and Review

Use concise, structural, evidence-backed reasoning; distinguish observation,
inference and unknowns. Do not introduce propaganda, narrative manipulation,
personal blame or short-term optics as success. External providers and AI models
gain no authority over evidence or project governance; ordinary reviewed
technical dependencies are a separate question.

Use `.github/PULL_REQUEST_TEMPLATE.md` to record scope, rationale, affected
files, applicable language impact, validation/limits, risks, rollback and handoff.
Never claim unrun tests, product acceptance, independent review or owner approval.

## Security and Sensitive Information

### DO NOT Commit
- Personal data
- Banking or financial documents
- Credentials, API keys, passwords
- Private agreements
- Sensitive diplomatic information
- Real names or identifying information from scenarios (use anonymized examples)

### If Sensitive Data is Accidentally Committed
1. Report immediately
2. Do not attempt to fix by deleting only
3. History rewriting may be required

## Testing and Validation

### Root Python and Tooling

From the repository root, in an isolated development environment using Python
3.12 to match `.github/workflows/ci.yml`. Use complete Git history (CI uses
`fetch-depth: 0`): historical adoption regressions cannot run from a shallow
clone. Linux EC2 isolation tests also need a real root-to-nobody UID transition
and observable `/proc` descendants; an incompatible sandbox is a validation
limitation, not permission to weaken those tests.

```bash
set -euo pipefail
python -m pip install -r requirements-dev.txt
python tools/check_mojibake.py .
python tools/check_narrative_consistency.py --input datasets/ai_risk_narratives/seed_claims.json --schema datasets/ai_risk_narratives/claim_record.schema.json --report out/narrative_consistency.json
python -m pytest -q
python benchmarks/run_benchmarks.py
```

The runtime-only tier is `requirements.txt` (Python 3.11+); it does not install
pytest/PyYAML. Root CI uses the development tier. PowerShell certification also
requires `pwsh` 7+ and runs `python -m pytest -q
tests/test_powershell_tooling_safety.py`; skips without `pwsh` are not a pass.
Native Rust validation is described in the Device Bridge instruction.

The separate `EC2 locked environment` job certifies Linux x86_64 CPython 3.12
with `ops/ec2/requirements-{runtime,validation}.lock`, hash-checked wheels and
two sealed offline installs. Reproduce that job's exact steps for EC2 changes;
never substitute a root `pip install` for locked-environment certification or
execute deployment scripts as tests. Benchmarks are non-blocking in the workflow
(`continue-on-error: true`); report their actual result separately.

Record the full tested SHA, command, OS/toolchain, exit result and skips. Check
live required-check publishers and current HEAD before a merge decision. A
missing, skipped, stale or manually dispatched product check is not implied by
a green root suite; GUI, real-Web, host capture and deployment need their own
exact-source evidence and applicable owner authorization. Do not dispatch them
or weaken checks merely to complete validation.

### Link Checking
- [Link Check workflow](workflows/link-check.yml) runs Lychee over `README.md`,
  `CONTRIBUTING.md`, `docs/CONTRIBUTING.md`, `docs/**/*.md` and
  `ops/aws/operator-url-intake/*.md`. The workflow does not explicitly select
  `.github/lychee.toml`; do not assume that file's exclusions are active.
- Failures in those configured targets fail that job. It does not cover all
  Markdown: `products/**`, `v1_core/**`, `.github/**`, most `ops/**` and other
  root documents are not covered. Validate changed links there separately;
  green Lychee is not evidence for omitted paths or externally served bytes.

## Additional Resources

- Main README: `/README.md`
- Contributing Guide: `/CONTRIBUTING.md`
- Start Here: `/docs/00_start_here.md`
- Workflow Overview: `/v1_core/workflow/README.md`
- Base Declaration (Kernel canonical): `/v1_core/languages/es/01_base_declaracion.md`
- Architecture (Kernel canonical): `/v1_core/languages/es/02_arquitectura_base.md`
- Operational Flow (Kernel canonical): `/v1_core/languages/es/03_flujo_operativo.md`
- English parity references: `/v1_core/languages/en/`
- Governance Documents: `/docs/governance/`

HUB_Optimus supports human judgment. Do not turn methodology goals, generated
prose, a passing narrow test or historical acceptance into a broader capability
or authorization claim.
