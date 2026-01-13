# HUB_Optimus — Translation Policy (No Drift)

## Purpose
HUB_Optimus must remain meaning-identical across languages.
Translations exist to increase accessibility, not to create alternative governance systems.

This policy prevents:
- conceptual drift,
- capture via translation,
- accidental placeholder commits,
- silent re-interpretation.

## Canonical Source of Truth
The canonical governance set lives in:
- `docs/governance/`

All other languages (e.g. `docs/de/governance/`) are mirrors of the canonical set.

## Non-Drift Rule (Binding)
Translations MUST preserve:
- meaning,
- definitions,
- section order,
- normative strength (MUST/SHALL/NOT),
- constraints and prohibitions.

Translations MUST NOT introduce:
- new concepts,
- exceptions,
- additional permissions,
- softened language,
- alternative “interpretations”.

If a translation diverges, it is considered invalid until corrected.

## Structural Mirror Rule
Every language folder MUST contain the same governance file set and filenames as the canonical folder.

Example:
- `docs/governance/KERNEL.md`
- `docs/de/governance/KERNEL.md`

## Change Workflow
1) Edit canonical (`docs/governance/...`) first.
2) Commit canonical changes.
3) Sync translations in a separate commit (preferred) or immediately after.
4) Run placeholder check (see below) before merging.

## Placeholder Prohibition
Placeholders are forbidden in any published documentation.

Forbidden patterns include (non-exhaustive):
- `PEGA AQUI`
- `<PEGA AQUI`
- `PLACEHOLDER`
- `TODO: translate`

Any commit containing placeholders in `docs/*/governance/*.md` must be rejected.

## Enforcement (Practical)
Maintainers/Custodians may block merges when:
- translations drift from canonical meaning,
- file sets differ,
- placeholders exist,
- governance changes were made only in non-canonical languages.

## Rationale
Translation drift is a known capture vector.
HUB_Optimus treats drift as a structural security failure, not as a stylistic difference.
