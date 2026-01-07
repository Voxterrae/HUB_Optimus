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
- short-term â€œwinsâ€ presented as success while increasing long-term instability,
- attempts to introduce coercive enforcement into HUB_Optimus.

---

## 2) Repository structure (how to contribute safely)

### `legacy/`
Historical v0 materials preserved for transparency.
- **Do not rewrite or â€œmodernizeâ€** legacy documents.
- Corrections should be added as v1 notes, not retroactively edited.

### `v1_core/`
The active Kernel and simulator.
- Changes here require higher scrutiny and must preserve meaning and structure.

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
- [v1_core/languages/01_base_declaracion.md](v1_core/languages/01_base_declaracion.md)
- [v1_core/languages/02_arquitectura_base.md](v1_core/languages/02_arquitectura_base.md)
- [v1_core/languages/03_flujo_operativo.md](v1_core/languages/03_flujo_operativo.md)

Kernel changes require:
- explicit justification,
- impact analysis,
- integrity-first review,
- synchronized language updates.

---

## 4) Language policy (single core, multiple languages)

- Folder structure and filenames must remain consistent across languages.
- English (`en`) is the reference language for structure and validation.
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
- do not â€œfix by deletingâ€ only; history rewriting may be required.

---

## 8) Code of conduct (minimal)

- Be respectful and precise.
- Disagree with ideas, not people.
- Keep discussions focused on system improvement.

---

## 9) License
Contributions are accepted under the repository license.
If no license is defined yet, contributions are assumed to be offered for inclusion under a future open-source license chosen by the maintainers.

---

## 10) DCO sign-off (required)
All contributions must include a Signed-off-by line in each commit.
Example:
Signed-off-by: Your Name <you@example.com>

By signing off, you confirm you have the right to submit the work under the repository license.

---

## 11) Contribution access (core-team only option)
Maintainers may require prior approval before accepting public contributions.
When restricted mode is active, unsolicited PRs may be closed; request approval first.
