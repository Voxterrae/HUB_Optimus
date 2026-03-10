# Contributing to HUB_Optimus

Thank you for your interest in contributing to HUB_Optimus.

HUB_Optimus is open-source by design, but **Kernel influence is integrity-gated**.
Use is open. Contribution is structured. The Kernel is protected.

---

## 1) Contribution philosophy

### What we value
- clarity over volume,
- structural reasoning over rhetoric,
- prevention over escalation,
- integrity and coherence over credentials,
- verifiable improvement over visibility.

### What we do not accept
- changes that weaken Kernel integrity protections,
- narrative manipulation or propaganda,
- personal scapegoating as analysis,
- short-term “wins” presented as success while increasing long-term instability,
- attempts to introduce coercive enforcement into HUB_Optimus.

---

## 2) Repository structure (how to contribute safely)

### `legacy/`
Historical v0 materials preserved for transparency.
- **Do not rewrite or “modernize”** legacy documents.
- Corrections should be added as v1 notes, not retroactively edited.

### `v1_core/`
The active Kernel and simulator.
- Changes here require higher scrutiny and must preserve meaning and structure.

---

## 2.1) Contributor zones

### Open zones (contributors welcome, no mandatory review gate)

| Path | What lives here |
|---|---|
| `docs/` (non-governance) | Onboarding guides, reading paths, translations |
| `tools/` | Maintenance scripts, auditing utilities |
| `tests/` | Regression tests, smoke tests |
| `examples/` | Example scenarios and usage samples |
| `legacy/` | Historical v0 materials (read-only — see above) |

### Protected zones (require maintainer review via CODEOWNERS)

| Path | Why it's protected |
|---|---|
| `v1_core/languages/` | Kernel specs — canonical (`es`) and parity (`en`) |
| `docs/governance/` | Charter, consensus process, trust layer |
| `.github/` | CI, issue forms, PR template, CODEOWNERS |
| `scenario.schema.json` | Runtime contract — changes break benchmarks |
| `run_scenario.py`, `hub_optimus_simulator.py` | Simulator core |
| `benchmarks/` | Deterministic output contract |

### How to pick up an issue

1. Find an issue labelled `good first issue` or in an open zone.
2. Comment on the issue to signal intent.
3. Wait for informal assignment (to avoid duplicate work).
4. Create a branch: `feat/<short-name>` or `chore/<short-name>`.
5. Open a focused PR linked to the issue (`Fixes #N`).

---

## 3) Contribution types

### A) Documentation improvements (low risk)
Examples:
- typo fixes,
- formatting,
- readability improvements (without meaning drift).

### B) Scenario contributions (recommended)
Add new scenarios under:
- `v1_core/workflow/`

Use the canonical template:
- [v1_core/workflow/04_scenario_template.md](v1_core/workflow/04_scenario_template.md)

Every scenario must include:
- trigger, structural context, incentive analysis,
- systemic evaluation, historical contrast,
- Kernel coherence check, final classification,
- memory integration notes.

### C) Meta-learning updates (medium risk)
Updates to:
- [v1_core/workflow/05_meta_learning.md](v1_core/workflow/05_meta_learning.md)

Must reference:
- which scenario(s) justify the new rule,
- what failure/success pattern it prevents or reinforces.

### D) Kernel changes (high risk)
Files like:
- [v1_core/languages/es/01_base_declaracion.md](v1_core/languages/es/01_base_declaracion.md) (canonical)
- [v1_core/languages/es/02_arquitectura_base.md](v1_core/languages/es/02_arquitectura_base.md) (canonical)
- [v1_core/languages/es/03_flujo_operativo.md](v1_core/languages/es/03_flujo_operativo.md) (canonical)
- [v1_core/languages/en/01_base_declaracion.md](v1_core/languages/en/01_base_declaracion.md) (parity)
- [v1_core/languages/en/02_arquitectura_base.md](v1_core/languages/en/02_arquitectura_base.md) (parity)
- [v1_core/languages/en/03_flujo_operativo.md](v1_core/languages/en/03_flujo_operativo.md) (parity)

Kernel changes require:
- explicit justification,
- impact analysis,
- integrity-first review,
- synchronized language updates.

---

## 4) Language policy (single core, multiple languages)

- Folder structure and filenames must remain consistent across languages.
- `docs/context/STATUS.md` is the source-of-truth when repository docs conflict.
- `v1_core/languages/es/` is canonical.
- `v1_core/languages/en/` is parity reference.
- Translations must preserve meaning; do not introduce conceptual drift.

---

## 5) How to propose changes (workflow)

1. Create a new branch:
   - `feat/<short-name>` or `chore/<short-name>`
2. Make a focused change:
   - one objective per PR
3. Open a Pull Request with:
   - clear summary,
   - rationale,
   - affected files,
   - scenario links (if applicable),
   - risks and mitigations (if kernel-adjacent).

### PR merge requirements

Before a PR can be merged, all of the following must be true:

- **Correct issue reference:** The PR must reference the correct issue. Double-check that the referenced issue matches the actual work done.
- **Use `Related to #N`, not `Closes #N`:** Contributors should link issues with `Related to #N`. Only maintainers close issues at merge time. Keywords like `Closes`, `Fixes`, or `Resolves` auto-close the referenced issue, which can accidentally close tracking issues or ledgers.
- **CI must pass:** All CI checks (pytest, benchmarks, kernel guard, link check) must be green.
- **Scope limited to one issue:** Each PR should address a single issue or objective. Do not bundle unrelated changes.
- **Description matches diff:** The files listed in the PR description must match the files actually changed.
- **Runtime changes require review:** Any PR that touches the simulator, schema, benchmarks, or CI configuration requires explicit maintainer review.

---

## 6) Integrity-first review

Contributions are reviewed for:
- coherence with Layer 0 principles,
- systemic framing (not personal blame),
- incentive awareness,
- prevention posture,
- clarity and traceability.

Repeated coherent contributions may be granted expanded review rights over time.
No one is granted Kernel influence by title alone.

---

## 7) Security and sensitive information

**Do not upload:**
- personal data,
- banking or financial documents,
- credentials, API keys, passwords,
- private agreements.

If sensitive data is accidentally committed:
- report immediately,
- do not “fix by deleting” only; history rewriting may be required.

---

## 8) Code of conduct (minimal)

- Be respectful and precise.
- Disagree with ideas, not people.
- Keep discussions focused on system improvement.

---

## 9) License
Contributions are accepted under the repository license.
If no license is defined yet, contributions are assumed to be offered for inclusion under a future open-source license chosen by the maintainers.
