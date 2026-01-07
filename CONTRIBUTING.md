# Contributing to HUB_Optimus

Thank you for your interest in contributing to HUB_Optimus.

HUB_Optimus is publicly readable, but **no rights are granted** unless and until a license is published.
Contributions may be accepted, but **Kernel influence is integrity-gated** and acceptance is maintainers-only.
The Kernel is protected.

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
- short-term "wins" presented as success while increasing long-term instability,
- attempts to introduce coercive enforcement into HUB_Optimus.

---

## 2) Repository structure (how to contribute safely)

### `legacy/`
Historical v0 materials preserved for transparency.
- **Do not rewrite or "modernize"** legacy documents.
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
- [v1_core/languages/en/01_base_declaracion.md](v1_core/languages/en/01_base_declaracion.md)
- [v1_core/languages/en/02_arquitectura_base.md](v1_core/languages/en/02_arquitectura_base.md)
- [v1_core/languages/en/03_flujo_operativo.md](v1_core/languages/en/03_flujo_operativo.md)

Kernel changes require:
- explicit justification,
- impact analysis,
- integrity-first review,
- synchronized language updates (when applicable).

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
- do not "fix by deleting" only; history rewriting may be required.

---

## 8) Code of conduct (minimal)

- Be respectful and precise.
- Disagree with ideas, not people.
- Keep discussions focused on system improvement.

---

## 9) License and inbound contribution grant

This repository currently operates in **restricted mode** under a "no license granted" policy.
Until an explicit open-source or commercial license is published, **no rights to use, copy, modify, or distribute** are granted to the public.

### Contributions (inbound grant)
If maintainers explicitly accept your contribution, you grant the maintainers and project stewards a **perpetual, worldwide, irrevocable, royalty-free license** to use, modify, reproduce, and relicense your contribution as part of HUB_Optimus.

Unsolicited PRs may be closed when restricted mode is active. If in doubt, open an Issue first.

---

## 10) DCO sign-off (required)

For any approved contribution, all commits must include a Signed-off-by line in each commit.

Use:
- `git commit -s -m "message"`

Example:
- `Signed-off-by: Your Name <you@example.com>`

By signing off, you confirm you have the right to submit the work and to grant the inbound license described above.

---

## 11) Contribution access (core-team only option)

Maintainers may require prior approval before accepting public contributions.
When restricted mode is active, unsolicited PRs may be closed; request approval first.
