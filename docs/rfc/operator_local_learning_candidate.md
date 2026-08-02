# Operator local learning candidates

## Status

Lifecycle: **Model-only prototype contract; not integrated into Operator**.

The module can construct and validate a local, human-authored learning candidate
when it is called explicitly. The current Operator UI does not load this module,
does not expose the workflow, and does not persist candidates. This patch is the
executable data model and test boundary for a future browser integration, not a
claim that meta-learning is already a product feature. It is not model training,
institutional memory, a truth score, or an automatic update to Core, the Semantic
Engine, GitHub, or any remote service.

The versioned data contract is
[`operator_learning_candidate.v1.schema.json`](../../site/operator/schemas/operator_learning_candidate.v1.schema.json).
The executable validator and state machine are in
[`learning-candidate.v1.js`](../../site/operator/learning-candidate.v1.js). The
method reference remains the versioned repository workflow
[`v1_core/workflow/05_meta_learning.md`](../../v1_core/workflow/05_meta_learning.md),
whose exact SHA-256 is bound into every candidate.

## What the loop does

In a future, separately reviewed integration, after Operator has prepared a
source-bound local draft, a human could explicitly:

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
five closure checks set to `true`; the model enforces both requirements rather
than relying on a future UI to disable a button.

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
| `stale` | The same case exists but its revision changed. | No. Review again and use a new candidate ID for changed content. |
| `invalid` | The case identity changed or referenced claim/evidence disappeared. | No. |

Editing source input or structural case records therefore makes derived
candidates stale or invalid. It never silently edits, accepts, rejects, or
deletes their history.

## In-memory store model, export, and deletion

The candidate module defines pure store operations and does not call browser
storage, the DOM, or any network API. A separate model-layer adapter now exists
in [`learning-store.v1.js`](../../site/operator/learning-store.v1.js), but the
current Operator HTML and service worker do not load or cache it. Consequently,
refreshing the current Operator still cannot recover a candidate and this RFC
does not claim a user-facing persistence feature.

- Maximum 50 candidates in the in-memory store model.
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
the caller's expected entry SHA-256 as the compare-and-swap token, retains the
candidate SHA-256 and case revision as diagnostic tokens, constructs and
validates the next complete store, and writes it within one read-write
transaction. The entry digest covers both candidate and freshness binding, so
a concurrent binding-only update also causes a conflict. Export requires the
same current tokens and never silently exports a newer local candidate.
Candidate and entry limits remain enforced and the complete store has an
additional hard ceiling of 16 MiB.

Version 1 is append-only per candidate ID in every state. A binding-only
freshness update may retain the exact candidate. The only candidate-byte change
permitted under that ID is a pure state transition: all content and the complete
history prefix remain byte-identical, while state, update time, and exactly one
appended transition event advance. Editing outcome, metrics, learning nodes,
provenance, creation time, or history requires a new candidate ID. Acceptance
additionally requires complete closure and a current binding. This intentionally
means that the model-layer prototype does not yet expose an edit-in-place API.
Version 1 also defines no `supersedes` or successor relation between candidate
IDs; adding a lineage link or same-ID draft editor is a future contract decision,
not behavior that the current adapter may infer.

The adapter has no storage fallback, network path, implicit database reset, or
silent eviction. It classifies failures as unavailable, blocked, corrupt,
quota, or conflict; handles blocked upgrades and version changes; and requires
explicit confirmation plus the expected store digest before clearing all
records. Import, export, candidate deletion, and case deletion preserve the
same validation and optimistic-concurrency boundary. Stored bytes are treated
as untrusted on every read.

Only a public URL origin or an opaque stable ID may be retained as a source
reference. URL paths, queries, fragments, and credentials are not stored in a
learning candidate. No learning candidate is included in the analysis request,
case JSON, WhatsApp text, or shared draft summary.

## Boundary for future work

Loading either model-layer module from Operator, adding UI, performing browser
integration and end-to-end QA, or claiming the workflow is available to users
requires a separate implementation change. Promotion to repository knowledge, a remote database,
cross-device sync, ranking, model training, or an automatic Core/Semantic Engine
update requires a separate governance-reviewed decision. If a future local UI
uses `accepted`, it will mean only that the operator accepted that candidate on
that device.
