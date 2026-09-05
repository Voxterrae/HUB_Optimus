# RFC lifecycle

The machine-readable lifecycle registry is
[`registry.v1.json`](registry.v1.json). It covers every RFC Markdown file in
this directory and is verified against the repository commit recorded in its
`baseline`.

The registry reports evidence; it does not create authority. In particular:

- merging proposal text records that text in Git history;
- merging is not, by itself, acceptance or ratification;
- implementation does not retroactively approve an RFC;
- an `Accepted` or `Implemented` state requires a recorded human decision,
  owner, ratifier, and evidence;
- `null` means the repository does not currently record that fact.

## Lifecycle states

| State | Meaning |
| --- | --- |
| `Proposed` | An idea is recorded but is not yet a reviewable RFC draft. |
| `Draft` | Reviewable proposal text exists; it is not accepted and authorizes no implementation by itself. |
| `Accepted` | A human decision record accepts the RFC; implementation may still be absent. |
| `Partially Implemented` | Some linked behavior exists, but the RFC is not fully realized. This state does not substitute for a missing decision record. |
| `Implemented` | Accepted scope is linked to implementation and current verification evidence. |
| `Superseded` | A later decision replaces the RFC and is linked from the registry. |
| `Rejected` | A human decision record rejects the proposal. |

## Registry field semantics

- `record_pr` identifies the Pull Request that places the lifecycle record in
  protected repository history.
- `decision_pr` identifies the Pull Request that places the decision record in
  protected repository history. When the accountable human decision originates
  in an issue or an exact issue comment, `decision_pr` identifies the Pull
  Request that incorporates or reconciles that external decision, and `note`
  MUST link the exact decision source. It does not mean that the Pull Request
  supplied the decision, is approved, or is authorized to merge.
- `ratifier` names the accountable human first. A repository account and its
  immutable ID may record the channel and provenance of that decision, but the
  account is not an independent human authority.

## Current snapshot

At the verified baseline commit
`d96fa7de64e5a27a3058d892ca31cf93d0fa0de7` from 2026-08-25, sixteen RFC
records were `Draft`. Operator Controlled URL Intake was `Partially
Implemented` because local/private code and tests existed, but no decision PR,
public deployment evidence, or full RFC implementation was recorded.

This reconciliation records the later owner decision accepting Operator Human-
Confirmed Atomic Claim Drafting. The candidate registry therefore reports
fifteen `Draft`, one `Accepted`, and one `Partially Implemented` record. Draft
PR #1921 was unapproved and unmerged when this reconciliation candidate was
prepared; this lifecycle transition authorizes neither merge nor deployment.

Repository capabilities are tracked separately in
[`../architecture/capability_status.md`](../architecture/capability_status.md).
The plain-language project boundary is
[`../context/PROJECT_OVERVIEW.md`](../context/PROJECT_OVERVIEW.md).
