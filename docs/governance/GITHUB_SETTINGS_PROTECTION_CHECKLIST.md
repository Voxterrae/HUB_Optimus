# GitHub Settings Protection Checklist

## Purpose

Document the expected and observed GitHub protection settings for
`Voxterrae/HUB_Optimus`.

This document records evidence. It does not itself change GitHub Settings,
workflows, CODEOWNERS, permissions, branches, runtime behavior, deployments, or
releases.

## Verification context

- Repository: `Voxterrae/HUB_Optimus`
- Default branch: `main`
- Verification date: 2026-08-20
- Verified `main` SHA: `30e985226347b4bc59b0e187b96633a09647ca42`
- Canonical active ruleset: `11665521` — `Protect main - owner governed`
- Approved ruleset payload SHA-256: `50739828a718b8f6d72a47a3d9d74b1d3657be27dc4fe3593f6cb8a1ed0ce4cb`
- Approved payload length: `1094` bytes
- Required-check integration: GitHub Actions, `integration_id=15368`
- Consolidation evidence: issue `#1680`, synthetic PRs `#1891` and `#1893`,
  and postflight receipt comment `#issuecomment-5357624828`
- Legacy ruleset `11637867`: deleted after snapshot export and postflight
  validation

## Status key

- `verified`: live evidence matches the expected protection.
- `intentional`: the observed setting is deliberately different from an older
  proposal and matches the owner-ratified governance model.
- `pending`: expected protection or external evidence remains incomplete.
- `unknown`: the setting could not be verified from available evidence.

## Checklist

| Setting | Expected state | Observed state | Evidence | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Ruleset-based protection for `main` | Enabled | `main` is protected by one active repository ruleset, `11665521`. Classic branch protection is not the active mechanism. | `gh api repos/Voxterrae/HUB_Optimus/rulesets`; `gh api repos/Voxterrae/HUB_Optimus/rules/branches/main`; issue `#1680` | verified | Rulesets, not the legacy branch-protection endpoint, are the source of truth for this branch. |
| Active branch rulesets | Exactly one active repository ruleset applies to `main` | Only `11665521` — `Protect main - owner governed` — remains active. Legacy ruleset `11637867` was deleted after export and validation. | Final receipt `HUB_OPTIMUS_LEGACY_RULESET_POSTFLIGHT_RESUME_V1`; issue `#1680` | verified | The previous overlap and role bypass were removed. |
| Pull request before merge | Required | The retained ruleset contains an active `pull_request` rule. | Ruleset `11665521` | verified | Direct unreviewed branch updates are not the intended path. |
| Native approving reviews | `0` under Option A | `required_approving_review_count: 0` | Ruleset `11665521`; issues `#1861`, `#1862` | intentional | The sole CODEOWNER cannot natively approve an owner-authored PR. |
| Native CODEOWNERS review | Disabled under Option A | `require_code_owner_review: false` | Ruleset `11665521`; `.github/CODEOWNERS`; issue `#1682` disposition | intentional | CODEOWNERS remains global review routing and authority evidence. Protected changes are gated by verified owner history, Founder Authority Guard, required checks, governance-issue linkage, and resolved conversations. |
| Conversation resolution | Required | `required_review_thread_resolution: true` | Ruleset `11665521`; synthetic review-thread validation in PR `#1893` | verified | All review threads must be resolved before merge. |
| Required status checks | Exact approved contexts required on the current head | `founder-authority`, `founder-authority-bootstrap`, `pytest`, `PowerShell tooling`, `guard`, `Risk classification`, and `lychee` are required and bound to GitHub Actions `integration_id=15368`. | Ruleset `11665521`; PRs `#1891`, `#1893`; issue `#1680` | verified | `Benchmarks` remains non-blocking because its workflow contract is `continue-on-error: true`. |
| Strict required-check policy | Enabled | `strict_required_status_checks_policy: true` | Ruleset `11665521` | verified | The PR must be evaluated against the current target-branch state. |
| Founder Authority Guard | Required exact-head semantic result and workflow integrity | Both `founder-authority` and `founder-authority-bootstrap` are required contexts. | Live validation issue `#1884`, PR `#1886`, ruleset `11665521` | verified | The semantic check is published on the exact PR head from trusted-base policy. |
| Kernel Guard | Required | Context `guard` is required. Removing `allow-kernel-change` caused a controlled failure; restoring it recovered the check. | PR `#1893`; runs `32168092385` and `32168175799` | verified | The label is a visible, reviewable authorization signal, not a ruleset bypass. |
| PR Safety | Required | Context `Risk classification` is required. | Ruleset `11665521`; synthetic validation PRs | verified | Workflow behavior was not changed by the settings operation. |
| Link Check | Required | Context `lychee` is required. | Ruleset `11665521`; synthetic validation PRs | verified | Multiple successful runs may appear, but the ruleset contains one required context. |
| CI test suite | Required | Contexts `pytest` and `PowerShell tooling` are required. | Ruleset `11665521`; synthetic validation PRs | verified | There is no single stable required context named `CI`. |
| Force pushes | Blocked | Active `non_fast_forward` rule. | Ruleset `11665521` | verified | Non-fast-forward updates to `main` are prohibited. |
| Branch deletion | Blocked | Active `deletion` rule. | Ruleset `11665521` | verified | `main` cannot be deleted through the protected path. |
| Required signed commits | Enabled | Active `required_signatures` rule. | Ruleset `11665521` | verified | Hardware-backed owner-key enrollment remains a separate future strengthening step. |
| Linear history | Enabled | Active `required_linear_history` rule. | Ruleset `11665521` | verified | Combined with squash-only merge. |
| Merge method | Squash only | `allowed_merge_methods: ["squash"]` | Ruleset `11665521` | verified | Merge commits and rebase merges are not allowed by the retained ruleset. |
| Admin or role bypass | None | `bypass_actors: []` | Ruleset `11665521`; issue `#1683` | verified | Any future bypass proposal requires a new visible governance decision and evidence trail. |

## Required contexts

All required contexts are bound to GitHub Actions application ID `15368`:

```text
founder-authority
founder-authority-bootstrap
pytest
PowerShell tooling
guard
Risk classification
lychee
```

## Diagnostic note on `mergeable_state`

The synthetic PR `#1893` repeatedly reported:

```text
mergeable=true
mergeable_state=blocked
GraphQL mergeStateStatus=BLOCKED
reviewDecision=null
```

This persisted after the legacy ruleset was deleted, with the approved checks
green and review threads resolved. The generic aggregate value is therefore
recorded as an opaque diagnostic observation, not as evidence that a listed
protection is absent and not as merge authorization.

## Governance disposition

- Issue `#1681` remains open until this checklist update is reviewed and merged.
- Issue `#1683` remains open until this checklist update is reviewed and merged.
- Issue `#1682` was closed as `not_planned`; native CODEOWNER self-approval was
  superseded by owner-ratified Option A in `#1861` / `#1862`.
- Future GitHub Settings mutations require an explicit issue, immutable IDs or
  exact names, preflight snapshots, a rollback boundary, and postflight evidence.
