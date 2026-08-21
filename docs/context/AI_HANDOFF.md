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

## Public surface capability registry boundary

Issue `#1888` governs reconciliation between the canonical repository, the
public GitHub Pages artifact, and the protected Sites mirror. Pull request
`#1889` is the foundation record for the human-reviewed capability registry and
its validation contract. The current merge, deployment, and receipt state must
always be read from the exact issue, pull request, commit, checks, and Pages run;
this handoff does not turn a draft or proposed SHA into merged evidence.

The foundation paths are:

- `site/data/capability-registry.v1.json`;
- `site/data/capability-registry.v1.schema.json`;
- `docs/architecture/public_surface_sync.md`;
- the focused registry tests.

The registry separates a public static surface, a public browser runtime, a
production service, production writes, and live external transport. It must keep
merged evidence distinct from draft pull requests, draft stacks, and issue-only
work. Evidence type, reference, immutable commit, repository path, and URL must
remain mutually consistent and testable.

The existing Pages workflow is triggered by changes under `site/**` and
`docs/**`, but deploys the exact `site/` artifact. Therefore any merge of the
foundation requires an explicit owner decision that covers the resulting Pages
deployment and a post-merge receipt for the merged commit, tree, workflow run,
and public registry/schema resources.

Outstanding slices remain separate:

1. the visible presentation must consume the reviewed registry through its own
   scoped pull request and must not present draft or issue-only work as live;
2. the protected Sites mirror must be synchronized only after the canonical
   presentation change is reviewed, merged, deployed, and bound to an exact SHA;
3. Sites publication, access changes, tenant mutation, external transport, and
   production-service writes require their own explicit owner authorization.

Until those slices have exact repository and platform evidence, future operators
must continue to describe GitHub Pages as the canonical public static surface
and Sites as a non-authoritative, separately synchronized mirror.

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
