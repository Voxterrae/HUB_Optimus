# Operator local learning candidates

## Status

Lifecycle: **Local Operator prototype; draft RFC, not ratified**.

Operator now loads the versioned model and IndexedDB adapter and exposes a fifth,
always-visible local review step after source-bound draft preparation. The form is
locked until the current page holds a prepared `operator-source-bound-v1` draft.
It then lets a human create, inspect, transition, export, import, and explicitly
delete candidate records on that device. This is an executable local review loop,
not model training, institutional memory, a truth score, or an automatic update
to Core, the Semantic Engine, GitHub, or any remote service. Availability in the
repository is not evidence of a public deployment or governance ratification.

The versioned data contract is
[`operator_learning_candidate.v1.schema.json`](../../site/operator/schemas/operator_learning_candidate.v1.schema.json).
The executable validator and state machine are in
[`learning-candidate.v1.js`](../../site/operator/learning-candidate.v1.js). The
method reference remains the versioned repository workflow
[`v1_core/workflow/05_meta_learning.md`](../../v1_core/workflow/05_meta_learning.md),
whose exact SHA-256 is bound into every candidate.

## What the loop does

After Operator has prepared a source-bound local draft, a human can explicitly:

1. state the actual outcome in one sentence;
2. record three to ten observable signals and link each one to existing claim
   and evidence records;
3. write a diagnosis using the repository's explicit diagnostic categories;
4. identify one gap and one minimum proposed change;
5. record three to five manual metrics, the next experiment, and the closure
   checklist;
6. inspect the candidate and choose `draft`, `accepted`, or `rejected`.

Creating a candidate does not imply acceptance. Every state transition requires
a human note and is appended to visible history. A candidate can move from
`draft` to `accepted` or `rejected`, and from either reviewed state back to
`draft`; it cannot flip directly between `accepted` and `rejected`.
Local acceptance additionally requires a current live-case snapshot and all
five closure checks set to `true`; the model enforces both requirements in
addition to the UI disabling an unavailable transition.

## Structural links

The record is a small explicit graph rather than a free-form memory blob.

| From | Relation | To | Meaning |
| --- | --- | --- | --- |
| Outcome | `OUTCOME_OF_CASE` | Case | The recorded outcome belongs to this case revision. |
| Evidence | `SUPPORTS_ATTRIBUTION`, `SUPPORTS_CLAIM`, or `CONTRADICTS_CLAIM` | Claim | Existing source-bound relation; no truth is inferred. |
| Signal | `SIGNAL_REFERENCES_CLAIM` | Claim | The human linked an observation to an existing claim. |
| Signal | `SIGNAL_GROUNDED_IN_EVIDENCE` | Evidence | The signal retains evidence provenance. |
| Diagnosis | `DIAGNOSIS_INTERPRETS_SIGNAL` | Signal | The diagnosis explicitly covers every recorded signal. |
| Diagnosis | `DIAGNOSIS_REFERENCES_EVIDENCE` | Evidence | The diagnosis retains evidence provenance. |
| Gap | `GAP_IDENTIFIED_BY_DIAGNOSIS` | Diagnosis | The proposed gap follows from the recorded diagnosis. |
| Action | `ACTION_ADDRESSES_GAP` | Gap | The minimum change addresses that gap. |

Dangling references, duplicate semantic edges, invalid relation signatures, and
candidates without an evidence-to-claim relation are rejected before insertion
into the in-memory store model or export. Version 1 rejects every
`system-suggested` relation; it accepts only human-authored learning links and
the source-bound case relations imported from the live case snapshot. Any later
automated suggestion requires a new version and separate governance review.

## State and freshness are different

`state` records a human decision. `freshness` compares the candidate with the
current case revision and is never allowed to rewrite that decision.

| Freshness | Meaning | Local acceptance allowed? |
| --- | --- | --- |
| `current` | Case identity, revision, claims, and evidence still match. | Yes, by explicit human action. |
| `stale` | The same case exists but its revision changed. | No. Return to draft and review again. |
| `invalid` | The case identity changed or referenced claim/evidence disappeared. | No. |

Editing source input or structural case records therefore makes derived
candidates stale or invalid. It never silently edits, accepts, rejects, or
deletes their history.

## Local store, export, and deletion

The candidate module defines pure store operations and does not call browser
storage, the DOM, or any network API. Operator loads it before the inline UI,
then loads [`learning-store.v1.js`](../../site/operator/learning-store.v1.js).
The service worker precaches both modules and the JSON schema. Candidate records
therefore survive an ordinary page reload in the same browser profile when
IndexedDB is available. There is no `localStorage` fallback: unavailable,
blocked, corrupt, quota, and conflict states fail closed and are presented in the
active Operator language.

- Maximum 50 candidates in the local store model.
- Maximum 256 KiB per candidate entry.
- Maximum 1 MiB per imported export envelope.
- JSON is canonicalized to Unicode NFC, LF line endings, and sorted object keys
  before checksumming.
- Export/import preserves IDs, links, state, method reference, and history and
  rejects unknown versions, checksum drift, or ID conflicts.
- A full store never evicts an older record silently.
- Deleting candidates for a case removes the candidate graph as one unit, so no
  orphaned local relations remain.

The model-layer adapter uses IndexedDB database
`hub_optimus_operator_learning_v1`, version 1. Its sole object store contains
exactly one keyed `operator_learning_store.v1` record: the complete validated
store. Each mutation reads and validates the latest untrusted record, checks
the caller's expected full-entry SHA-256 together with candidate and case-revision
tokens, constructs and validates the next complete store, and writes it within
one read-write transaction. Candidate and entry limits remain enforced and the
complete store has an additional hard ceiling of 16 MiB.

The adapter and UI have no storage fallback, learning-network path, implicit database reset, or
silent eviction. It classifies failures as unavailable, blocked, corrupt,
quota, or conflict; handles blocked upgrades and version changes; and requires
explicit confirmation plus the expected store digest before clearing all
records at model level. The UI exposes candidate and case deletion with explicit
confirmation, but not a weak or implicit clear operation. Import, export,
candidate deletion, and case deletion preserve the
same validation and optimistic-concurrency boundary. Stored bytes are treated
as untrusted on every read.

Each `candidate_id` is append-only after creation. An existing record may receive
only a separately validated freshness-binding update or one pure state transition
whose history is the previous immutable prefix plus exactly one event. Changing
content, provenance, metrics, closure, or graph structure requires a new
candidate ID; the UI exposes no in-place content editor.

Only a public URL origin or an opaque stable ID may be retained as a source
reference. URL paths, queries, fragments, and credentials are not stored in a
learning candidate. No learning candidate is included in the analysis request,
case JSON, saved draft memory, WhatsApp text, shared draft summary, hash
fragment, clean Operator URL, or controlled-intake network request. Imported
text is rendered with DOM text nodes and candidate JSON is shown in an LTR
`pre`; no imported value is interpreted as HTML.

## Browser interaction boundary

- The form starts with three signal rows and permits at most ten. Every signal
  must cite at least one claim and one evidence record from the current case.
- The outcome, diagnosis, categories, evidence links, gap, proposed change,
  reason, success criterion, three required ratings, decision, next experiment,
  closure checklist, and creation note are explicit human inputs. Operator does
  not generate a diagnosis or acceptance decision.
- The inspector shows human state, live freshness, structured content, complete
  transition history, and canonical JSON. Re-evaluating freshness after a case
  edit does not rewrite the stored human state or history.
- Export is a local JSON download. Import is capped at 1 MiB, validates version,
  checksum, schema, graph, and history before an atomic insert, and never silently
  overwrites an existing candidate ID.
- `accepted` is a local human decision only. The transition is disabled and the
  model rejects it unless all five closure items are true and the complete live
  case snapshot is current.
- Labels and explanations are available in English, Spanish, German, Russian,
  Hebrew, and Simplified Chinese. Canonical enum and relation tokens remain
  untranslated inside the versioned record.

## Boundary for future work

Public deployment and real-device browser QA remain separate release evidence;
repository tests cannot prove either. Promotion to repository knowledge, a remote database,
cross-device sync, ranking, model training, or an automatic Core/Semantic Engine
update requires a separate governance-reviewed decision. `accepted` means only
that the operator accepted that candidate on that device.
