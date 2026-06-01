# GitHub Settings Protection Checklist

## Purpose
Document expected repository protection settings and mark observed state as
`verified`, `pending`, or `unknown`.

This document does not change GitHub Settings, workflows, CODEOWNERS, branch
rules, automation, or runtime behavior.

## Verification Context
- Repository: `Voxterrae/HUB_Optimus`
- Default branch: `main`
- Verification date: 2026-05-15
- Evidence source: GitHub CLI/API read-only queries and repository files

## Status Key
- `verified`: observed evidence matches the expected protection.
- `pending`: expected protection is not fully observed, or needs explicit maintainer confirmation.
- `unknown`: current state cannot be verified from available evidence.

## Checklist

| Setting | Expected state | Observed state | Evidence | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Branch protection for `main` | Enabled | `main` reports `protected: true` through GitHub branch metadata. Legacy branch-protection endpoint returns `404 Branch not protected`, so protection appears ruleset-based rather than legacy branch protection. | `gh api repos/Voxterrae/HUB_Optimus/branches/main`; `gh api repos/Voxterrae/HUB_Optimus/branches/main/protection` | verified | Track this as ruleset-based protection, not legacy branch protection. |
| Active branch rulesets | At least one active ruleset applies to `main` | Two active branch rulesets apply to `main`: `Protect main (restricted)` and `protect-main`. | `gh api repos/Voxterrae/HUB_Optimus/rulesets`; `gh api repos/Voxterrae/HUB_Optimus/rules/branches/main` | verified | Duplicate or overlapping rulesets should be reviewed before future settings changes. |
| Required PR before merge | Enabled | Active `pull_request` rules are present for `main`. | `gh api repos/Voxterrae/HUB_Optimus/rules/branches/main` | verified | Current rules show `required_approving_review_count: 0`; review strength is tracked separately below. |
| Required status checks | CI, Kernel Guard, Link Check, and PR Safety should be required before merge | Workflows exist and run on PRs, but no required status-check rule was observed through legacy branch-protection endpoints or active branch rules. | `.github/workflows/ci.yml`; `.github/workflows/kernel-guard.yml`; `.github/workflows/link-check.yml`; `.github/workflows/pr-safety-check.yml`; branch protection status-check endpoint returned `404 Branch not protected` | pending | Decide whether required checks should be enforced through rulesets in a separate settings-change issue. |
| CODEOWNERS review | Enabled for protected paths | `.github/CODEOWNERS` maps protected paths to `@Voxterrae`, but active pull-request rules report `require_code_owner_review: false`. | `.github/CODEOWNERS`; `gh api repos/Voxterrae/HUB_Optimus/rules/branches/main` | pending | CODEOWNERS exists, but enforcement through GitHub Settings is not currently observed. |
| Force pushes | Disabled | Active `non_fast_forward` rules apply to `main`. | `gh api repos/Voxterrae/HUB_Optimus/rules/branches/main` | verified | This blocks non-fast-forward updates, including force pushes. |
| Branch deletion | Restricted or disabled | Active `deletion` rules apply to `main`. | `gh api repos/Voxterrae/HUB_Optimus/rules/branches/main` | verified | This protects `main` from branch deletion through rulesets. |
| Required signed commits | Enabled if required by repository policy | Active `required_signatures` rules apply to `main`. | `gh api repos/Voxterrae/HUB_Optimus/rules/branches/main` | verified | Present as an active ruleset protection. |
| Linear history | Enabled if required by repository policy | Active `required_linear_history` rules apply to `main`. | `gh api repos/Voxterrae/HUB_Optimus/rules/branches/main` | verified | Present as an active ruleset protection. |
| Admin or role bypass | Restricted or explicitly documented | One active ruleset has no bypass actors. Another has a `RepositoryRole` bypass actor with `bypass_mode: always`. | `gh api repos/Voxterrae/HUB_Optimus/rulesets/11637867`; `gh api repos/Voxterrae/HUB_Optimus/rulesets/11665521` | pending | Confirm whether the role bypass is intentional and document who may use it. |
| Merge method restrictions | Expected merge methods should be explicit | One ruleset allows `merge`, `squash`, and `rebase`; the other allows `squash` only. | `gh api repos/Voxterrae/HUB_Optimus/rules/branches/main` | pending | Overlapping rulesets make the effective merge-method policy harder to audit. |

## Follow-up Items
- Decide whether required status checks should be enforced in GitHub rulesets.
- Decide whether CODEOWNERS review should be enforced in GitHub rulesets.
- Confirm and document the intended admin or repository-role bypass policy.
- Review overlapping branch rulesets before making any future settings changes.
- Keep any settings mutation out of this PR; open a separate issue for configuration changes.
