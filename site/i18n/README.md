# Public portfolio translation status

Operator interface catalog version: `1.3.2`.

This directory records the translation boundary for the static public portfolio and
the complete Operator interface. It does not translate the repository or the
constitutional kernel. Technical JSON keys, code, IDs, enums, hashes, timestamps,
URLs, and commands remain language-neutral and direction-isolated.

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
| `en` | LTR | Portfolio, 404, and complete Operator interface | Existing portfolio/primary terminology audit under #1736; Advanced is an AI-assisted draft; named qualified human review required |
| `es` | LTR | Portfolio, 404, and complete Operator interface | Existing portfolio/primary terminology audit under #1736; Advanced is an AI-assisted draft; named qualified human review required |
| `de` | LTR | Portfolio, 404, and complete Operator interface | Existing portfolio/primary terminology audit under #1736; Advanced is an AI-assisted draft; named qualified human review required |
| `ru` | LTR | Portfolio, 404, and complete Operator interface | Machine-assisted draft; qualified human review required |
| `he` | RTL | Portfolio, 404, and complete Operator interface | Machine-assisted draft; qualified human review required |
| `zh-Hans` | LTR | Portfolio, 404, and complete Operator interface, Simplified Chinese only | Machine-assisted draft; qualified human review required |

No named reviewer is recorded for any locale. A named qualified human reviewer must be
recorded in
[`locale-metadata.v1.json`](locale-metadata.v1.json) before a locale can be described as
human-reviewed or professionally translated. The automated and AI-assisted checks in
#1736 establish terminology, register, claim parity, and structural coverage; they do
not establish certified or professional human review.

## Operator boundary

The primary Operator flow and the Advanced / Audit JSON workflow are available in all
six interface locales. Labels, validation states, URL-intake status, source-bound draft
summary, local learning controls, Advanced editing/persistence/handoff controls, result
readouts, errors, confirmations, and next actions are localized. Raw JSON, code,
commands, URLs, identifiers, hashes, timestamps, and enum values are never translated.
These translations are machine/AI-assisted and still require a named, qualified human
language review.

Public Operator creates a local, source-bound review draft from the complete text
pasted by the operator. It does not send or retrieve a supplied URL during intake;
that exact URL remains local, unverified attribution and may be included by an
explicit share action. Automatic URL retrieval belongs to a
separate private Operator and is not enabled by this public artifact. The public
Operator does not execute the Semantic Engine, establish truth, or verify provenance;
neither does localization change those limits. A localized interface therefore does
not promote the browser prototype into a released analysis service.
Triage does not verify stated provenance.

## Document-link language resolution

Changing the interface language does not imply that every repository document has a
reviewed translation. The portfolio resolves each document link through
[`document-routes.v1.js`](document-routes.v1.js) and shows separate language-relation
and maturity labels next to the link.

Language relation:

- `source` identifies a document written in the selected interface language.
- `fallback` makes the absence of a document in the selected language explicit and
  links to the declared source language instead.
- `data` identifies a structured artifact whose records are multilingual or are not
  routed as a single prose language.

Maturity is a separate optional field and uses repository vocabulary:

- `canonical` identifies an authoritative source designated by repository policy.
- `review-needed` identifies an available non-authoritative translation whose accuracy
  and freshness are not evidenced, currently the German Governance Intelligence file.

A route without a maturity label makes no maturity claim. In particular, the Spanish
meta-learning workflow is linked as an available source without promoting its current
repository classification. `fallback` describes language availability only and never
reduces or changes a document's authority on its own surface.

Repository document routes use a fixed commit so that the visible language badge and
the linked content cannot drift independently. Same-site translation metadata,
geographic attribution, and termbase records ship atomically with the static artifact.
Code, tests, commands, identifiers, hashes, timestamps, and other language-neutral
implementation links are not routed as translated prose.

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
