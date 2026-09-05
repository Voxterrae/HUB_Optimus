# RFC: Operator Human-Confirmed Atomic Claim Drafting

## Status

- **Accepted** by Benjamin Gerrit Hoff through the protected GitHub account
  `@Voxterrae` (immutable user ID `249308740`).
- Decision record: [issue #1920 comment
  `5430873541`](https://github.com/Voxterrae/HUB_Optimus/issues/1920#issuecomment-5430873541).
- Bounded correction and reconciliation authority: [PR #1921 comment
  `5431264847`](https://github.com/Voxterrae/HUB_Optimus/pull/1921#issuecomment-5431264847).
- Decision-pinned RFC snapshot: commit
  `d96fa7de64e5a27a3058d892ca31cf93d0fa0de7`, tree
  `21ec2710f61df06c099d64366cd88c3d3da5d024`, and RFC blob
  `088c10e36dfc451414028b30c7c761b2660c17d6`.
- At the time of this reconciliation, the candidate implementation was tracked
  by Draft PR #1921. Listing that PR is traceability, not implementation
  approval.
- Proposed draft identity: `operator-source-bound-v2`.
- No schema change, public activation, merge, deployment, GitHub Pages, AWS,
  DNS, audiovisual intake, truth verdict, institutional ledger, or
  public-service change is authorized by this acceptance record or by green
  checks.

The current `operator-source-bound-v1` flow remains authoritative until a
conforming implementation satisfies this RFC and its executable tests, receives
independent review, and is merged through the protected process.

Within this unactivated v2 candidate, `exact_excerpt_sha256`,
`confirmation_sha256`, `source_proposal_id`, and the `source_span_*` keys are
reserved provenance markers. Their presence is fail-closed and requires a valid
v2 attestation; generic or v1 extensions must use separately namespaced keys.

The pinned RFC blob is the text accepted by the decision record. This
reconciliation records that external decision and the expressly authorized
fail-closed corrections in PR #1921. The correction authority is limited to
reconciling this Accepted record, producing a new verifiable candidate head,
running CI, and requesting independent review; it does not authorize merge or
deployment and does not broaden the RFC's operational authority.

## Problem

Operator currently creates one attributed claim for each human-selected source
passage. A passage can contain several independently challengeable assertions,
so one broad claim may hide disagreement, uncertainty, or missing evidence.

HUB_Optimus needs a bounded stage between passage selection and case preparation:

```text
selected source passage
-> atomic claim drafts
-> human edit and confirmation
-> structural coverage check
-> operator-source-bound-v2 draft
```

This stage structures what the selected material asserts. It does not verify the
assertions or claim to find every assertion in the complete source.

## Decision

`operator-source-bound-v2` MUST keep source evidence and canonical claim wording
separate.

- An **exact evidence excerpt** is the human-selected text retained from the
  canonicalized source representation, with its locator and fingerprint. It is
  immutable evidence of what that retained representation displayed, not proof
  that the statement is true.
- A **canonical claim draft** is one bounded, independently reviewable assertion
  used within one case revision. “Canonical” means the working statement for
  that case, not canonical repository knowledge or verified truth.
- A **paraphrase** is any human-edited claim wording. It remains a paraphrase
  even if its characters match the original span or another substring of the
  excerpt, and MUST NOT be rendered or exported as an exact quotation.

One excerpt may support several claim drafts. In this first version, every claim
occurrence stays bound to exactly one selected excerpt; apparently equivalent
claims from different excerpts are not merged automatically. A future governed
ledger may relate those occurrences without erasing either provenance chain.
Exact evidence text MUST never be overwritten by a paraphrase.

## Atomicity boundary

A claim draft SHOULD express one assertion with one independently reviewable
truth condition. Attribution, causality, quantity, event occurrence, intent,
and predicted effect SHOULD be split when one could be challenged without
challenging the others.

The distinction between “a speaker made this statement” and “the underlying
statement is true” MUST remain visible. Recording either claim does not accept
it. Evidence-to-claim links in this candidate MUST retain
`support_scope=attribution-only`; they record attribution, not corroboration.

Mechanical sentence or clause suggestions MAY seed the editor. They are
navigation aids only. They MUST NOT add unsupported meaning, infer hidden
claims, assign evidence quality, or become confirmed without human action.

## Human confirmation gate

Before Operator prepares a v2 draft, a human MUST be able to:

1. inspect each exact evidence excerpt beside its proposed claim drafts;
2. edit, add, remove, or split claim wording;
3. record every mechanical proposal explicitly as reviewed or omitted, without
   deleting omitted proposals from the review ledger;
4. identify a claim expression as an exact source quotation or a human
   paraphrase;
5. inspect the Unicode-code-point source span retained for every claim;
6. confirm that every retained item is one separately reviewable claim; and
7. confirm the complete evidence-to-claim links and selected-passage coverage.

The preparation action MUST fail closed while an unconfirmed claim, dangling
link, or uncovered passage remains. Confirmation means only that the human has
reviewed the draft structure; it is not verification, endorsement, or a truth
decision.

## Coverage rule

Coverage is structural and limited to the selected passages.

- Every confirmed claim MUST link to at least one exact evidence excerpt.
- Every mechanical proposal MUST have an attested `reviewed` or `omitted`
  disposition. A pending proposal blocks preparation. An omitted proposal stays
  in the review ledger and MUST NOT produce a claim or relation.
- Every selected excerpt MUST link to at least one confirmed claim in this first
  version. Material selected only for context must be removed from the claim
  passage selection and recorded separately as operator context.
- Claim/evidence links MUST remain explicit one-excerpt-to-many-claims
  relations in v2. No cross-excerpt equivalence is inferred.
- Unselected, unavailable, dynamic, audio, or video content is outside the
  coverage claim.

Passing coverage MUST be described as “all selected passages reviewed,” never
as “all source claims found” or “source verified.”

## Language and identifier stability

Claim, evidence, and relation identifiers MUST be opaque and non-localized.
Claim occurrence identifiers MAY be deterministically bound to the source
fingerprint, excerpt identifier, and canonical claim expression so a material
edit creates a new identity. They MUST NOT depend on visible UI labels or an
interface translation. Switching the Operator interface language MUST NOT
regenerate identifiers, translate stored claim text, or change the prepared
case revision.

Each claim expression and evidence excerpt MUST retain its original Unicode text
without translating it when the interface language changes. This first version
does not infer or label content language. A translated expression may share a
conceptual claim only after explicit human confirmation; the system MUST NOT
infer cross-language equivalence. A meaning-changing edit requires renewed
review and MUST NOT be hidden behind a translated label.

Every claim occurrence MUST also retain an inspectable absolute
Unicode-code-point source span inside its selected excerpt. Exact claim wording
must equal that exact span. Human-edited wording remains a paraphrase even when
its characters happen to occur elsewhere in the excerpt; it retains the source
span reviewed as its provenance boundary.

## Staleness and revision binding

A prepared v2 draft MUST bind to the source fingerprint and intake-derived
source reference, selected excerpt locators and identifiers, exact evidence
text and type, confirmed claim expressions, and the complete relation set with
its identifiers. Evidence, source and relation identifiers are deterministic;
changing them or their intake provenance makes the draft stale.

The stored v2 record projection and the human-confirmation checksum MUST feed a
separate attestation checksum. That checksum detects an ordinary edit to the
intake record, source references, claims, evidence or relations and requires a
new review. It is an integrity checksum, not a digital signature: it does not
prove who confirmed the draft and cannot resist a malicious editor who can
rewrite the record and recompute hashes.

Changing any of those inputs makes the prepared draft stale and blocks analysis,
sharing, saving, or learning-candidate creation until the human reviews and
confirms a new revision. Changing only the interface language or other
presentation state does not make the draft stale.

Existing learning candidates follow the freshness rules in
[`operator_local_learning_candidate.md`](operator_local_learning_candidate.md):
a changed case revision cannot silently rewrite or preserve acceptance of an
older candidate.

No v1 draft is silently upgraded to v2. No stale v2 draft is rewritten as v1.

## Separation from PR #1918

PR #1918 concerns the controlled URL-intake pilot boundary, including its
authentication, request limits, infrastructure, and cost controls. This RFC is
a browser-local claim-drafting boundary after a human has source text to review.

- It does not change PR #1918, CDK, AWS, authentication, quotas, DNS, or the URL
  endpoint.
- Merging or deploying PR #1918 does not enable `operator-source-bound-v2`.
- Implementing v2 does not deploy or make PR #1918 public.
- A future v2 implementation may consume the same bounded successful intake
  response, but retrieval failure behavior remains unchanged.
- Video, JavaScript-only, or otherwise unavailable content remains unsupported
  unless a separate governed intake capability is approved.

## Non-goals

This RFC does not authorize or claim:

- truth adjudication, verification scoring, source ranking, or LLM-as-judge;
- automatic semantic extraction, hidden inference, or autonomous confirmation;
- complete claim discovery across an entire document, site, feed, audio, or
  video;
- automatic translation or automatic cross-language equivalence;
- an institutional epistemic ledger, remote memory, cross-device sync, model
  training, or automatic Core/Semantic Engine updates;
- crawler, OCR, transcription, browser automation, provider, or connector work;
- public accusations, enforcement, sanctions, profiling, or consequential
  decisions about people;
- enterprise storage, billing, AWS, DNS, deployment, or roadmap changes.

## Acceptance tests for a future implementation

A reviewed implementation MUST provide executable tests showing that:

1. one synthetic compound passage can produce multiple independently confirmed
   claims without changing its exact evidence excerpt;
2. a paraphrase is never presented or exported as exact evidence or quotation;
3. every mechanical proposal remains in an attested review ledger with an
   explicit reviewed or omitted disposition;
4. every claim retains a valid absolute Unicode-code-point source span, and an
   exact claim equals that span;
5. unconfirmed claims, pending proposals, dangling links, and uncovered excerpts block v2
   preparation;
6. every confirmed claim and selected excerpt satisfies the coverage rule;
7. interface-language changes preserve opaque IDs and case revision identity;
8. source, excerpt, proposal disposition, claim, or relation edits invalidate the prepared draft and
   any derived freshness binding;
9. current v1 drafts and local learning candidates remain readable and are not
   silently migrated;
10. the implementation performs no new network request and does not alter the
   PR #1918 infrastructure boundary; and
11. all supported Operator languages explain confirmation, paraphrase,
    coverage, staleness, and the non-verification boundary consistently.

Tests prove only the reviewed code paths. They do not prove source truth,
translation equivalence, deployed behavior, or complete semantic coverage.

## Rollback

A future implementation MUST remain reversible by disabling or reverting the v2
drafting path and returning new preparation to `operator-source-bound-v1`.

Rollback MUST NOT relabel v2 records as v1, delete existing v1 local records,
rewrite learning history, or create a network migration. Uncommitted v2 drafts
may be exported for inspection or explicitly discarded by the human. Because
this RFC creates no AWS resource, rollback requires no infrastructure deletion.

## Risks

- A human may introduce meaning drift while paraphrasing. Keep exact evidence
  visible beside the claim and require explicit confirmation.
- Mechanical clause splitting may perform unevenly across languages. Treat all
  suggestions as editable and unconfirmed.
- A coverage indicator may imply false completeness. Limit it visibly to the
  selected passages; record contextual material outside the claim-passage
  selection.

## Validation

For the browser-local candidate tracked by issue #1920:

```bash
PYTHONPATH=. python -m pytest \
  tests/test_operator_claim_decomposition.py \
  tests/test_operator_pwa_product_actions.py \
  tests/test_operator_primary_i18n.py \
  tests/test_operator_learning_ui.py
node --check site/operator/claim-decomposition.v1.js
git diff --check
```
