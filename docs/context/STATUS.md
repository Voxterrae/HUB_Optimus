## Status freshness

This file records stable repository policy and high-level status. For current PR/issue state, GitHub Issues, Pull Requests, and CI are authoritative.

### Canonical languages policy (v1)

**v1_core/** (normative spec):
- **Canonical (source of truth): es**
- **Reference translation / parity target: en** (kept close, but es wins on conflicts)

**docs/** (onboarding & navigation):
- Priority languages: **es, de, en**
- Additional languages: ca, fr, ru (structure complete; translation progressive)
- Stub languages: **zh-Hans, he** (repository directories `zh` / `he`; governance stubs; full translation pending)

File presence is structural evidence only, not proof of translation. The
versioned, machine-verifiable maturity record for onboarding and governance is
`docs/i18n/maturity.v1.json`. Hebrew is declared right-to-left. The current
Chinese scope is Simplified Chinese (`zh-Hans`); Traditional Chinese
(`zh-Hant`) is not yet in scope.

Canonicality is surface-specific: `docs/governance/` is the English canonical
governance source under `docs/governance/TRANSLATION_POLICY.md`, while the
canonical v1 methodology remains Spanish under `v1_core/languages/es/`.

**Source-of-truth rule:**
- The project-wide precedence order is defined once in
  [`SOURCE_OF_TRUTH.md`](SOURCE_OF_TRUTH.md).
- This file is authoritative for canonical-language, locale, and parity
  conflicts. It does not override GitHub `main`, live GitHub object state,
  governance sources, runtime contracts, source code, or executable evidence
  in their own domains.
- For HUB_Optimus v1, the canonical methodology source is
  `v1_core/languages/es/`.
- English and other languages are reference or parity translations unless
  explicitly stated otherwise.
- Local labels such as "English source" or EN/ES cross-links are
  navigation/parity aids only; they do not redefine canonical authority for
  `v1_core`.

**Planned switch (later, not now):**
- Once en reaches stable parity, we may declare **en as canonical** for a future version (v1.1 or v2).

## Meta-learning file status

- `.github/copilot-instructions.md` identifies `v1_core/workflow/05_meta_learning.md` as the meta-learning update location.
- Other meta-learning files exist as compatibility targets, translations, or unclassified copies and need separate canonical/parity/legacy classification.
- Do not consolidate, delete, or rewrite meta-learning files without a scoped issue or PR.
