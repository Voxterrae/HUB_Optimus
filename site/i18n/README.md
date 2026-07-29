# Public portfolio translation status

This directory records the translation boundary for the static public portfolio. It does
not translate the repository, the constitutional kernel, or the Operator interface.

## Authority

- Canonical HUB_Optimus v1 remains Spanish under
  [`docs/context/STATUS.md`](https://github.com/Voxterrae/HUB_Optimus/blob/main/docs/context/STATUS.md).
- All six interface dictionaries, including Spanish, are presentation layers. They do
  not supersede the canonical Spanish v1 methodology.
- No constitutional translation is ratified by this locale pack.
- A translation cannot change an implemented capability into a released service, or an
  RFC into an implemented capability.

## Locale status

| Locale | Direction | Scope | Status |
|---|---:|---|---|
| `en` | LTR | Existing portfolio interface baseline | AI-assisted terminology and register audit under #1736; named qualified human review required |
| `es` | LTR | Existing portfolio interface translation | AI-assisted terminology and register audit under #1736; named qualified human review required |
| `de` | LTR | Existing portfolio interface translation | AI-assisted terminology and register audit under #1736; named qualified human review required |
| `ru` | LTR | Portfolio and 404 interface | Machine-assisted draft; qualified human review required |
| `he` | RTL | Portfolio and 404 interface | Machine-assisted draft; qualified human review required |
| `zh-Hans` | LTR | Portfolio and 404 interface, Simplified Chinese only | Machine-assisted draft; qualified human review required |

No named reviewer is recorded for any locale. A named qualified human reviewer must be
recorded in
[`locale-metadata.v1.json`](locale-metadata.v1.json) before a locale can be described as
human-reviewed or professionally translated. The automated and AI-assisted checks in
#1736 establish terminology, register, claim parity, and structural coverage; they do
not establish certified or professional human review.

## Operator boundary

The portfolio description and limitation notice are translated. The Operator application
itself remains in its existing language. Operator performs deterministic browser-side
triage; it does not execute the Semantic Engine. Triage does not verify stated
provenance.

## Versioned records

- [`locale-metadata.v1.json`](locale-metadata.v1.json) records scope, method, review
  requirement, reviewer, and field-level status for each locale.
- [`termbase.v1.json`](termbase.v1.json) records the interface terminology used for
  semantic parity. Its protected-interface-label records explain the intentionally
  untranslated `Labs` and `Issues` controls; other unchanged product names are listed
  separately as protected names.

Language reviewers should review both rendered text and these records. Hebrew review
must include keyboard order, focus order, mixed-direction product names, URLs, numbers,
and small-screen layout. Simplified Chinese review does not establish Traditional Chinese
coverage.
