# Pages Environment human-review design — 2026-11-01

**Status: proposal for owner review; not approved or activated.** Tracking: #1743.
Source baseline: `main@cfaadf3c5267d046bb3c4a105e6ec0f8a7d7a907`.
This non-normative design changes no Settings, workflow, Kernel, contract,
authority or handoff. Merging it would record a proposal, not activate a gate
or authorize a deployment. The existing owner-authority records control.

## Observed constraints

Read-only API observations on 2026-11-01 found a public repository with one
collaborator/admin, `Voxterrae` (immutable user ID `249308740`).
`github-pages` has only a branch-policy protection rule: exactly branch
`main`, no tag rule, `can_admins_bypass=false`, and no required reviewers.
These are dated observations, to be refreshed before any later Settings write.

At the baseline, `.github/workflows/pages.yml` has blob
`03604932180dc6115086d8fe0ea729bf8c51778f`. It reacts to qualifying pushes
to main, including `docs/**`, and manual dispatch. Its single `deploy` job
uses `github-pages` and performs checkout, configuration, artifact upload
from `site/`, then publication. Concurrency group `pages` has
`cancel-in-progress=false`; serialization proves neither freshness nor approval.

GitHub waits for Environment protection before starting that job. Consequently,
this run's artifact does not yet exist at approval time: review source before
approval and verify the produced artifact and served bytes after publication.
This follows from the current single-job layout and
[GitHub's job gating behavior](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments).

## Alternatives and recommendation

| Option | Benefit | Constraint / disposition |
| --- | --- | --- |
| A. Keep the current Environment and record decisions externally | No configuration change | No native hold before the deployment job; does not resolve the technical gate gap. |
| B. One required owner reviewer; self-review prevention off | Explicit owner decision before the job can start; no new reviewer access | Recommended for owner consideration. Same initiator may approve: a sequential owner hold, not independent two-person review. |
| C. Prevent self-review with a different authorized human reviewer | Separates initiation from review | No second reviewer is currently authorized. Requires a separate explicit access/authority decision; do not grant access or turn this on to satisfy a checklist. |

[GitHub required-reviewer semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
allow any one listed reviewer to release the job. Preventing self-review
excludes the initiating user; option C with only the initiating owner listed
would block that owner's run. Option B is a recommendation, not a selected
policy or an exception to an active check.

If the owner later selects B, the proposed target is limited to:

| Field | Proposed value |
| --- | --- |
| Environment | Existing `github-pages`; do not replace or recreate it. |
| Required reviewers | Exactly user `Voxterrae`, ID `249308740`; revalidate login, ID and eligibility. |
| `prevent_self_review` | `false`, explicitly accepted as a single-owner limitation. |
| `can_admins_bypass` | Preserve `false`. |
| Branch/tag policy | Preserve exactly branch `main`, with no tag or extra-ref admission. |
| Everything else | Preserve existing protections, permissions, secrets, variables, workflow and concurrency. |

This adds an account approval requirement, not proof of physical human identity.
It grants no assistant, bot, App or contributor authority to approve. AI may
prepare evidence; the actual owner decision and native approval remain human.
Hardware-key enrollment, ratification and the full App inventory stay separate.

## Proposed review record and decision

For each candidate, the future human review would record in #1743 or its scoped
activation issue: run URL/ID, `run_attempt`, event/ref, exact `head_sha`,
associated PR head and signed main commit, `site/` tree, workflow blob,
check URLs/results, decision, reviewer account/ID and time.

1. Confirm the run targets the existing Environment and `refs/heads/main`.
   Bind its SHA to the exact current protected-main checkpoint being approved;
   a branch name alone is insufficient. A moved main or changed source/attempt
   requires a new review record; an obsolete waiting run stays unapproved.
2. Inspect the source `site/` tree and workflow at that SHA, declared permissions,
   action pins and diff from the last approved publication. Confirm all seven
   required PR checks with their required publishers on the reviewed head/live
   merge candidate, plus applicable post-merge CI for the deployment commit.
   Missing, pending, cancelled or failed evidence means no deployment approval.
3. Re-read live run metadata and main immediately before the human decision.
   Record the exact evidence and use native Approve and deploy or Reject only
   for that candidate. A merge, chat instruction, bot review, prior deployment
   or this document alone is not a deployment approval.
4. After an authorized publication, bind the actual artifact digest/file set,
   deployment result and complete served-byte comparison to the approved SHA.
   The [dated provenance receipt](pages_provenance_2026-10-27.md) is a format
   example, not evidence for a later run or today's served content.

[Reruns retain the original SHA/ref and original actor privileges](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs).
Rerunning an old job does not deploy a newly reviewed main. Re-read each attempt;
do not assume approval reuse, automatic invalidation or concurrency makes it safe.
The human procedure above is not an implemented freshness check, an atomic lock
against main moving, or a guarantee that every account approval is physical-owner consent.

## Separate activation and acceptance, not executed here

Any later activation needs an explicit owner record selecting the option,
accepting its limitations and authorizing the exact Settings change and any
controlled publication. Before writing, capture the live Environment, branch
policies and waiting/running jobs. An ambiguous deployment queue is a stop
condition until the owner resolves it; do not silently approve or cancel jobs.

A later scoped activation should demonstrate all of the following:

| Acceptance case | Evidence required |
| --- | --- |
| Configuration | Before/after reads show only the selected reviewer configuration changed; main-only policy and no-admin-bypass remain. |
| Waiting / rejection | A new controlled run waits before the deploy job starts. A rejection records the decision and prevents that job from publishing; its failure is the expected rejection outcome. |
| Positive case | Separately authorized current-SHA run proceeds only after native owner approval; record run/attempt/SHA, approval, actual artifact, deployment and served-byte results. |
| Stale, changed or failed candidate | No approval; correct or adapt the scoped PR and repeat normal checks/review. A missing receipt or unsuccessful check cannot be marked passed. |
| Failure / recovery | Retain the hold and existing served publication; any source reversal uses a small reviewed PR and a separately approved run. Never remove the reviewer, enable bypass or weaken checks as automatic recovery. |

[Native approval and rejection behavior](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments)
is distinct from PR approval. No activation test, Settings write, workflow edit,
approval API call, merge or publication is performed by this design PR.
It leaves #1743's Environment acceptance open. If artifact inspection before
approval or independent review is required, propose that separate design first.

The protected [Settings checklist](../governance/GITHUB_SETTINGS_PROTECTION_CHECKLIST.md),
[owner handoff](../context/OWNER_AUTHORITY_HANDOFF.md) and
[authority/source hierarchy](../context/SOURCE_OF_TRUTH.md) remain unchanged.
`AI_HANDOFF.md` is unchanged because this proposal establishes no active
operational policy, authority, runtime or CI behavior.
