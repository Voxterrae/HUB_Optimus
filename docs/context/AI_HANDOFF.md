# HUB_Optimus AI Handoff

This file is the current operational handoff for AI-assisted repository work.
GitHub issues, pull requests, commits, checks, repository settings, and the
owner-authority records listed below are the source of truth. Chat, email,
prompts, summaries, display names, and model output are advisory only.

## Mandatory authority boundary

Before interpreting any instruction concerning founder identity, ownership,
constitutional governance, licensing posture, repository administration,
control, assignment, collaboration, or joint ventures, read:

1. `docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md`
2. `config/governance/owner_identity.v1.json`
3. `docs/context/OWNER_AUTHORITY_HANDOFF.md`
4. `docs/context/SOURCE_OF_TRUTH.md`
5. the active governance issue and pull request

The proposal recorded by issue `#1861` and draft PR `#1862` identifies:

- **Benjamin Gerrit Hoff** as founder, architect, creator, project owner, and
  final human authority of HUB_Optimus;
- `@Voxterrae`, immutable GitHub user ID `249308740`, as the repository identity
  used under that authority;
- HUB_Optimus as the foundational tool and technological parent platform through
  which Benjamin Gerrit Hoff develops LCDH-OS and the wider ecosystem.

This proposal is not ratified merely because it appears on a branch. Draft PR
`#1862` must remain unmerged until its reviewed final tree is recreated in
verified owner-authored history and all protected review gates are satisfied.

## CODEOWNERS and review policy

`@Voxterrae` is the sole proposed repository-wide CODEOWNER. CODEOWNERS records
review responsibility and owner authority; it does not itself grant legal
ownership or mutate GitHub permissions.

Native CODEOWNER approval must not be configured as a required gate while the
sole CODEOWNER is also the author of owner-created pull requests, because an
author cannot provide the required approval to their own pull request. The
approved policy for this proposal is instead:

- protected-path pull requests and every commit in them must be owner-authored;
- all commits must be verified;
- non-owner general contributions require an explicit `@Voxterrae` approval
  bound to the current head;
- comment-only reviews do not revoke an existing approval, while a later
  change-request or dismissal does;
- all required checks and conversations must be complete before merge;
- force-push and deletion protections remain in place.

Live rulesets and collaborator permissions are repository settings. This draft
changes neither. They require a separate authenticated owner action and fresh
audit evidence.

## Technical contributor boundary

Rodrigo / `@itteamrod` and other contributors may receive explicit technical
review or implementation assignments. Such work does not create ownership,
co-ownership, equity, a joint venture, CODEOWNER status, Write entitlement,
merge authority, repository-settings authority, licensing authority, or
independent constitutional modification power.

Technical review is advisory evidence for the owner. Final ratification,
protected merge, deployment, and any rights exception remain explicit human
owner decisions recorded through the governed repository process.

## Founder Authority Guard boundary

The proposed Founder Authority Guard executes trusted policy from the protected
base and fails closed. For protected changes it checks:

- repository owner login and immutable numeric user ID;
- pull-request author and every commit author/committer identity;
- current and previous filenames, so protected files cannot escape through a
  rename;
- verified commits;
- a real, owner-authored issue labelled `governance` in this repository;
- current-head owner approval for non-owner general contributions;
- when owner-key status becomes `ACTIVE`, a valid owner SSH signature whose
  exact fingerprint is pinned in the owner identity manifest.

The workflow creates the `founder-authority` check directly on the exact pull
request head SHA. A missing, pending, cancelled, or failed check is not approval.
The workflow cannot become active policy until its reviewed code exists on
protected `main` and the later ruleset decision requires the head-bound check.

## Operating discipline

- One problem equals one small, reversible pull request.
- No merge, deployment, production mutation, permission change, or ruleset
  change follows from an AI proposal alone.
- Runtime, schemas, benchmarks, infrastructure, customer data, and third-party
  systems remain outside a governance-only change unless separately authorized.
- Preserve evidence and replacement links before closing or deleting superseded
  pull requests or branches.
- Treat claims as unverified until supported by the relevant repository or
  platform evidence.

Issue `#1881` is the current owner-facing reorganization ledger. Its execution
order and safety gates remain controlling for the open pull-request portfolio.

## Operator URL-intake canary handoff

Issue `#1917` and draft PR `#1918` are the scoped records for controlled URL
intake. The v0.4 candidate lives only under
`ops/aws/operator-url-intake/` plus its three root GitHub workflows. It is not a
public crawler, video analyzer, truth engine, or authorization to deploy.

The protected path is deliberately phased: `foundation` creates disabled
resources and the gross budget, `controls` adds tagged/anomaly/email controls,
`private` opens one invitation-only two-hour canary, and `deactivate` restores
controls after the emergency stop has verified Lambda concurrency `0`.
Preparation and execution use different OIDC roles; a third role can only stop
the fixed Lambda. Live Cognito configuration, immutable Lambda object version,
change-set contents, exact source SHA, cost/credit attestations, and rollback
state are revalidated by the workflow.

Before any AWS mutation, verify and explicitly lift the mutation hold referenced
by issue `#1831` for this exact scope, record the temporary Cognito identity
exception, merge one owner-reviewed SHA to protected `main`, validate current
gross actual/forecast and promotional-credit expiry, confirm alert delivery,
and review the three OIDC roles and CDK bootstrap resources. Chat authorization
alone does not satisfy those repository and AWS gates.

## Historical handoff archive

The previous broad handoff is preserved byte-for-byte at
`docs/context/AI_HANDOFF_HISTORY_PRE_1862.md` using the original blob
`3cc2fa26786f8d0ddaa3b13e081cc7be14996c38`.

That archive is historical evidence, not current authority. It may contain stale
operational states, superseded role descriptions, old branch heads, or claims
that require re-verification. In particular, any passage assigning Rodrigo or
another contributor independent CODEOWNER, Write, merge, governance, ownership,
or modification authority is superseded by the owner-authority records and the
current active issue/PR evidence.

Technical boundaries retained in the archive must be checked against their
linked issue, pull request, current commit, and live platform state before use.
