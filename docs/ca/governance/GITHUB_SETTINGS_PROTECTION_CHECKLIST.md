# GitHub Settings Protection Checklist

## Purpose

Record expected protections and dated live observations. This document changes no
GitHub setting, workflow, CODEOWNERS entry, authority rule, or runtime behavior.
A successful check is technical evidence; it does not grant merge or deployment
permission.

## Verification context

- Repository: `Voxterrae/HUB_Optimus`; default branch: `main`.
- Read-only inspection date: **2026-09-14 (UTC)**.
- Repository baseline: `5cb923c38e8ec0f45468c29268c79dcc3b06b822`.
- Evidence: authenticated GitHub CLI REST GET responses, the live ruleset API,
  and the ten workflow YAML files at that baseline.
- Tracking: #1743 (settings attestation), #1687 (secret-exposure protections),
  #1931 (proposed workflow-default restriction), #1906 (publisher trust).
- This observation supersedes the 2026-05-15 snapshot for the settings inspected
  below. Git history preserves that earlier record.
- Settings are mutable and must be read again immediately before any future
  change. Repository files and public availability cannot certify live settings.

## Status key

- `verified`: the stated live value was observed; this does not certify the
  repository as a whole or guarantee absence of compromise.
- `pending`: a concrete follow-up or owner decision remains.
- `unknown`: available evidence cannot establish the broader claim.
- Explicitly disabled or unconfigured features remain described as such.

## Main protection

| Setting | Observed state | Status | Evidence / consequence |
| --- | --- | --- | --- |
| Active main ruleset | One active repository ruleset: `11665521`, `Protect main - owner governed`, applies to `refs/heads/main`. | verified | Ruleset collection and detail GET; the old overlapping-ruleset description is historical. |
| PR and merge method | PR required; only squash allowed for `main`. | verified | Ruleset `pull_request` rule. Repository-wide merge and rebase options are also enabled, but the narrower main rule allows squash only. |
| Required checks | Seven contexts, all bound to GitHub Actions integration `15368`: `founder-authority-bootstrap`, `pytest`, `PowerShell tooling`, `guard`, `Risk classification`, `lychee`, `founder-authority`. | verified | Required-status-check rule; latest passing runs alone would not prove enforcement. |
| Up-to-date candidate | `strict_required_status_checks_policy=true`. | verified | Required-status-check rule. |
| Review conversations | `required_review_thread_resolution=true`. | verified | PR rule. |
| Native approvals and CODEOWNER review | Approving review count 0; CODEOWNER review, stale-review dismissal, and last-push approval false. | verified | Observed configuration, not a claim that human review is unnecessary. The owner-only policy in `AI_HANDOFF.md` explains why authors cannot self-approve through the native CODEOWNER gate. |
| Force push and deletion | `non_fast_forward` and `deletion` rules active. | verified | Applies to main; does not authorize deletion of other branches. |
| Signed commits and linear history | `required_signatures` and `required_linear_history` active. | verified | A valid GitHub signature does not establish hardware-key enrollment. |
| Bypass | `bypass_actors=[]`; `current_user_can_bypass=never`. | verified | Authenticated ruleset detail. |
| Auto-merge and automatic branch deletion | Both repository options false. | verified | Repository metadata. |
| Founder-authority publisher trust | Required contexts still use generic GitHub Actions integration `15368`. | pending | #1906 retains the dedicated-publisher migration and exact-authorization hardening. Current green checks do not close that trust-root gap. |

The founder/owner identity manifest still records
`PENDING_HARDWARE_BACKED_KEY_ENROLLMENT`. This checklist does not amend the
[Founder Ownership and Authority Charter](FOUNDER_OWNERSHIP_AND_AUTHORITY.md),
[owner identity manifest](../../../config/governance/owner_identity.v1.json), or
[owner handoff](../../context/OWNER_AUTHORITY_HANDOFF.md).

## Security features and Actions defaults

| Setting | Observed state | Status | Evidence / consequence |
| --- | --- | --- | --- |
| Secret Scanning | enabled | verified | Authenticated repository `security_and_analysis.secret_scanning.status`. No alert contents or credentials were read. |
| Push Protection | enabled | verified | `secret_scanning_push_protection.status`. This is not proof that no secret was ever committed. |
| Non-provider patterns / validity checks | Both disabled. | pending | Repository security metadata; assess applicability separately before any opt-in. |
| Dependency Graph | Authenticated SBOM export succeeded and contained 11 packages. | verified | Dependency-graph SBOM endpoint; this confirms populated dependency data, not complete dependency coverage. |
| Dependabot alerts | Enabled endpoint returned successful empty response. | verified | GET `vulnerability-alerts`; alert contents were not inspected. |
| Dependabot security updates | enabled; not paused | verified | Repository metadata and `automated-security-fixes` endpoint. |
| Private vulnerability reporting | enabled | verified | `private-vulnerability-reporting` endpoint. |
| CodeQL default setup | `not-configured`. | verified | `code-scanning/default-setup`; default setup is not active. |
| Broader code-scanning coverage | Not established. | unknown | Analysis-list request returned HTTP 404 and a scope warning. No credential scopes were expanded. Do not infer absence of all custom/external scanning from this response. |
| Actions permission policy | enabled; `allowed_actions=all`; `sha_pinning_required=false`. | pending | Repository-wide settings permit more than the immutable pins checked by current repository tests. A platform-enforced restriction needs its own compatibility review and owner decision. |
| Default GITHUB_TOKEN authority | `default_workflow_permissions=write`; `can_approve_pull_request_reviews=true`. | pending | #1931 proposes `read` and `false`. No settings write has occurred. |
| Explicit workflow permissions | All ten main workflows declare permissions; the retirement execute job has its own explicit write block. | verified | Static YAML inventory at the pinned baseline. It does not certify every pending branch or invoked action. |

The proposed change in #1931 affects repository defaults and automated approving
reviews. It does not remove explicitly declared permissions or fix the separate
publisher-identity gap in #1906.

## GitHub Pages and documentation surfaces

| Setting | Observed state | Status | Evidence / consequence |
| --- | --- | --- | --- |
| Pages build mode | `workflow`; status `built`; API source metadata `main:/`. | verified | Pages GET. Build metadata is not byte-for-byte provenance of the currently served site. |
| Custom domain / HTTPS | `huboptimus.dev`; `https_enforced=true`; certificate approved, expiry reported as 2026-11-21. | verified | Pages GET. No DNS, certificate, or deployment change was made. |
| Environment branch policy | `github-pages` uses custom policies with exactly one branch policy, `main`. | verified | Environment and deployment-branch-policy GET responses. |
| Environment bypass | `can_admins_bypass=false`. | verified | Environment GET. |
| Required environment reviewers | No required-reviewer rule; the only observed protection rule is the branch policy. | pending | Human deployment-review design remains in #1743. This observation does not authorize an automatic deployment. |
| Served-site provenance | Not re-attested in this settings audit. | unknown | Before a later deployment, bind the approved source SHA to the served routes and byte receipts. The previous off-main concern in #1743 remains separate. |
| Wiki and Projects switches | Both enabled. | verified | Repository metadata. Feature switches do not certify content completeness or a populated Project board. |

Wiki sources already live under [docs/wiki](../../wiki/README.md). Preserve that
versioned source and its governed publication process rather than creating a
second independent documentation source.

## Read-only evidence routes

All repository-relative API paths below use
`repos/Voxterrae/HUB_Optimus/`:

- repository metadata; `branches/main`; `rulesets`; `rulesets/11665521`;
- `actions/permissions`; `actions/permissions/workflow`;
- `pages`; `environments/github-pages`;
  `environments/github-pages/deployment-branch-policies`;
- `vulnerability-alerts`; `automated-security-fixes`;
  `private-vulnerability-reporting`;
- `dependency-graph/sbom`; `code-scanning/default-setup`;
  `code-scanning/analyses?per_page=1` (limited result described above).

No secret values, alert payloads, personal files, credential stores, account
history, or private LCDH material are part of this public evidence.

## Follow-up and authority

1. Review the exact two-field Actions proposal in #1931 through the protected
   owner process; re-read live values before any write.
2. Keep #1906 open for the dedicated founder-authority publisher and its canary
   evidence. Do not re-run retired/off-main bootstrap paths.
3. Resolve #1743's environment-review and served-site-provenance gaps before
   considering a new Pages deployment.
4. Under #1687/#1743, assess default CodeQL setup, optional secret-scanning
   features, and platform Action restrictions before proposing changes.
5. Keep this file a dated observation. Future settings writes need an explicit
   scoped record, post-write verification, and an approved recovery plan.

No merge, deployment, settings mutation, or new credential authority follows
from this documentation update.
