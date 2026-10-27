# GitHub settings audit receipt — 2026-10-27 UTC

Baseline: `main@285fa6e0fc2152a9ffc948ee1cbee749eb736e1e`.
Tracking: #1743; portfolio inventory remains in #1881. Authenticated owner CLI
GETs and the bounded public-HTML comparisons below record only the inspected
surfaces.

This is a non-normative maintenance receipt. It does not amend or replace the
protected [Settings Protection Checklist](../governance/GITHUB_SETTINGS_PROTECTION_CHECKLIST.md),
Kernel, Founder Charter, owner identity manifest or their authority. The
protected checklist remains byte-identical to the baseline. Existing dated
snapshots retain their original scope; this receipt grants no exception or
permission to change a protected path.

| Surface | Observed state | Status / boundary |
| --- | --- | --- |
| Repository identity/access | Owner account `Voxterrae`, immutable user ID `249308740`; repository ID `1115264109`; one collaborator/admin; zero invitations, deploy keys and webhooks. | verified; no access grant or revocation. |
| Main ruleset | `11665521` active on `refs/heads/main`; no bypass actors and caller bypass `never`; PR, squash, signatures, linear history, resolved conversations, deletion and force-push protection retained. | verified; no rule changed. |
| Required publishers | `founder-authority` requires dedicated App `4705710`; `founder-authority-bootstrap`, `pytest`, `PowerShell tooling`, `guard`, `Risk classification` and `lychee` require Actions App `15368`; strict freshness enabled. | verified; #1906 retains its remaining scoped work, not a repeat of the completed publisher migration. |
| Native review policy | Approval count `0`; CODEOWNER, stale-review dismissal and last-push approval `false`; `require_extra_approval_for_unattributed_changes=true`. | verified; the documented sole-owner review model remains unchanged. |
| Repository merge options | Merge commits, rebase and squash enabled globally; auto-merge and automatic branch deletion disabled. | verified; the narrower main ruleset still allows squash only. Global restriction would also affect stacked bases and needs a separate decision. |
| Actions defaults | `default_workflow_permissions=read`; `can_approve_pull_request_reviews=false`. | verified; the former #1931 defaults are already applied. |
| Platform Actions policy | Actions enabled; `allowed_actions=all`; `sha_pinning_required=true`. | verified; SHA pinning is now platform-required. The selected-actions endpoint returns HTTP 409 under the all-actions policy, not evidence of an outage. |
| Actions retention | `days=90`; `maximum_allowed_days=90`. | verified; no retention or cache cleanup write. |
| CodeQL default setup | `configured`, default query suite; updated `2026-10-25T21:09:00Z`; Actions, JavaScript/TypeScript, Python and Rust returned by the API. | verified; the older not-configured observation is historical. |
| Security switches | Secret Scanning, Push Protection, Dependabot alerts/security updates and private vulnerability reporting enabled; updates not paused. Non-provider patterns and validity checks disabled. | verified; optional settings remain a separate applicability/owner decision. |
| Open alert aggregates | One HIGH CodeQL alert, number `5`, on this main baseline; zero open Dependabot alerts and zero open secret-scanning alerts in the returned pages. | verified aggregate only; #1974 already tracks the bundled-dependency finding. No dismissal, private diagnostic payload or claim of production exploitability. |
| Secret/variable inventory | Actions: three secrets and four variables. | metadata count only; no values read or published. |
| Pages/domain | `workflow`, `built`, API source `main:/`; `huboptimus.dev`; HTTPS enforced; certificate approved for that domain and `www.huboptimus.dev`, expiry `2027-01-20`. | verified settings; no DNS, certificate or deployment mutation. |
| Pages environment | `can_admins_bypass=false`; exactly one custom branch policy, `main`; branch-policy rule only, no required-reviewer rule. | verified; human deployment-review design remains pending under #1743. |
| Project board | Projects enabled; authenticated GraphQL returned `totalCount=0`, `hasNextPage=false` for repository-linked Projects v2. | verified empty linked inventory; no roadmap or board created. |
| Wiki | Live Wiki HEAD `bb04a3a331f0ed3b14720d3fe8073a392a69c38d` matches the publication receipt in #1972. | verified HEAD only; preserve source-first manual publication, not an inferred automatic sync. |
| Installed Apps / owner key | Full installed-App inventory not established by this credential; owner manifest remains `RATIFICATION_PROPOSED`, hardware-backed enrollment pending, no fingerprint enrolled. | unknown broader App coverage; no physical identity, hardware enrollment or new authority attested. |

## Limited served-HTML receipt

The latest successful Pages deployment inspected was
`20050a65e8d1288e9d01a511085d00a7b36ce54e`
([run 40229897939](https://github.com/Voxterrae/HUB_Optimus/actions/runs/40229897939)).
Its `site/` tree and the baseline main `site/` tree both equal
`67e832e3e6f5e7f0258d5bb58df5383bf8aa7677`.

Each route below returned HTTP 200 and its response bytes matched the exact
baseline source file by SHA-256:

| Public route | Source path at the baseline | Matching SHA-256 |
| --- | --- | --- |
| [Root](https://huboptimus.dev/) | `site/index.html` | `a49bbed7f526a40c46b4dd3e83ffbd8e0d209d5a827d77741ca9154062e30be8` |
| [Operator](https://huboptimus.dev/operator/) | `site/operator/index.html` | `e7c5c892383fd723d6702a6f57d0b5cc853a10fc1c9e30d448129074b81fa29b` |
| [Project intelligence](https://huboptimus.dev/obsidian-HUB_Optimus/) | `site/obsidian-HUB_Optimus/index.html` | `72c8357cd17025c01603ea65c6bb929df16ef39de199bd29d768ab17661ef983` |

This is a dated receipt for three HTML documents, not all served assets,
backend behavior, AWS deployment, customer data or a future release. It does
not close #1743's broader provenance or environment-review gates. The older
`pages/builds/latest` record is not the current workflow deployment authority.

## Refresh evidence and remaining work

Read-only evidence uses repository metadata; `rulesets/11665521`;
`actions/permissions`, `actions/permissions/workflow` and
`actions/permissions/artifact-and-log-retention`;
`code-scanning/default-setup`; the enabled-security endpoints; `pages`;
`environments/github-pages` and its deployment-branch policies; collaborator,
invitation, deploy-key and webhook collections; aggregate alert metadata;
repository-linked Projects GraphQL; and `git ls-remote` for the Wiki HEAD.
No secret, variable, token or credential value is part of this public receipt.

Keep #1743, #1906 and #1974 open for their exact remaining gates. No merge,
deployment, settings change, permission change, App installation, physical-key
enrollment, release edit or branch deletion follows from this documentation
refresh.

