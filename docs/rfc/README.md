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

## Current snapshot

At baseline commit `3ef199305c2d2d114f88aceb97b65a08b9f91b4a`,
fourteen RFC records are `Draft`. Operator Controlled URL Intake is
`Partially Implemented` because local/private code and tests exist, but no
decision PR, public deployment evidence, or full RFC implementation is
recorded.

Repository capabilities are tracked separately in
[`../architecture/capability_status.md`](../architecture/capability_status.md).
The plain-language project boundary is
[`../context/PROJECT_OVERVIEW.md`](../context/PROJECT_OVERVIEW.md).
