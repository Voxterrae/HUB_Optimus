## Status freshness

This file records stable repository policy and high-level status. For current PR/issue state, GitHub Issues, Pull Requests, and CI are authoritative.

### Canonical languages policy (v1)

**v1_core/** (normative spec):
- **Canonical (source of truth): es**
- **Reference translation / parity target: en** (kept close, but es wins on conflicts)

**docs/** (onboarding & navigation):
- Priority languages: **es, de, en**
- Additional languages: ca, fr, ru (structure complete; translation progressive)
- Stub languages: **zh, he** (directory + governance stub only; full translation pending)

**Source-of-truth rule:**
- If repository docs conflict, **this file (`docs/context/STATUS.md`) wins**.
- For HUB_Optimus v1, the canonical source-of-truth is `v1_core/languages/es/`.
- English and other languages are reference or parity translations unless explicitly stated otherwise.
- Local labels such as "English source" or EN/ES cross-links are navigation/parity aids only;
  they do not redefine canonical authority for `v1_core`.

**Planned switch (later, not now):**
- Once en reaches stable parity, we may declare **en as canonical** for a future version (v1.1 or v2).

## Meta-learning file status

- `.github/copilot-instructions.md` identifies `v1_core/workflow/05_meta_learning.md` as the meta-learning update location.
- Other meta-learning files exist as compatibility targets, translations, or unclassified copies and need separate canonical/parity/legacy classification.
- Do not consolidate, delete, or rewrite meta-learning files without a scoped issue or PR.
