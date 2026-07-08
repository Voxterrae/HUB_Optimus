# RFC: GitHub Platform Strategy for HUB_Optimus Evolution

## Status

- Draft / RFC only
- Planning and governance record
- Not implemented
- Tracks issue #1690
- No runtime, schema, dataset, fixture, benchmark, CI, dashboard, scoring, settings mutation, or LLM-as-judge change
- No GitHub Settings mutation authorized by this RFC
- No migration to a GitHub Organization authorized by this RFC

## Decision

Document a governed, traceable record of which GitHub platform capabilities HUB_Optimus should adopt now, defer to next, plan for later, or explicitly avoid — before contributor growth, external collaboration, or automation expansion increases the cost of course correction.

This RFC does not authorize any implementation. Every follow-up action requires a separate scoped GitHub issue.

## Purpose

HUB_Optimus uses GitHub as its source of truth for repository state, issues, PRs, CI, releases, governance docs, and operational handoff. As the project matures, additional GitHub capabilities become available or relevant. Adopting them without a governed frame risks:

- silent permission drift (capabilities enabled without reviewable decision);
- hidden-authority introduction (automation or AI agents operating outside the visibility principle);
- platform lock-in without explicit dependency acceptance;
- governance fragility during contributor onboarding.

This RFC creates a stable reference point. Each capability area is assessed against existing repository evidence and Layer 0 principles before any setting, workflow, or governance change is made.

## Scope

- Produce a decision record grounded in current repository evidence.
- Separate Now / Next / Later adoption and explicit rejections.
- Identify risks, dependencies, validation steps, and rollback paths.
- Preserve GitHub as the source of truth throughout.

## Out of scope

- No GitHub Settings mutation.
- No migration to a GitHub Organization.
- No Copilot or GitHub App automation.
- No dashboards, scoring systems, or LLM-as-judge.
- No roadmap changes without a separate approved RFC/issue.
- No immediate implementation of any recommendation.

## Evidence base

Current repository files reviewed for this RFC:

- `README.md`
- `AGENTS.md`
- `.github/CODEOWNERS`
- `.github/workflows/` (ci.yml, kernel-guard.yml, link-check.yml, pr-safety-check.yml, pages.yml, pr-quarantine.yml, repo-health-summary.yml, repo_maintenance_bot.yml)
- `docs/context/STATUS.md`
- `docs/context/AI_HANDOFF.md`
- `docs/governance/GITHUB_SETTINGS_PROTECTION_CHECKLIST.md`
- `docs/rfc/constitutional_governance_ai_regulatory_boundary.md`
- `docs/rfc/ip_confidential_disclosure_boundary.md`
- Open issues #1680–#1689 (governance hardening backlog)

All GitHub capability claims are grounded in the evidence listed above and official GitHub documentation. Claims not traceable to these sources are marked as unverified.

---

## RFC Answers

### 1. Which GitHub capabilities should HUB_Optimus adopt now, next, or later?

See the [Adoption Table](#adoption-table) below.

### 2. Which capabilities should be explicitly avoided for now?

See [Explicit Rejections](#explicit-rejections) below.

### 3. Which settings should be hardened before more contributors are onboarded?

The `GITHUB_SETTINGS_PROTECTION_CHECKLIST.md` records four `pending` items as of 2026-05-15:

- Required status checks not enforced through rulesets (CI, Kernel Guard, Link Check, PR Safety Check).
- CODEOWNERS review not enforced (`require_code_owner_review: false` in active pull-request rules).
- Admin/role bypass actor present with `bypass_mode: always`; intent undocumented.
- Overlapping rulesets (`Protect main (restricted)` and `protect-main`) make the effective merge-method policy ambiguous.

These four items constitute the minimum hardening gate before new contributors are onboarded. They are tracked in issues #1680–#1689 and must remain the immediate execution backlog unless this RFC identifies a critical blocker.

### 4. Should HUB_Optimus remain user-owned or eventually move to a GitHub Organization?

**Now:** Remain user-owned (`Voxterrae/HUB_Optimus`). The current single-maintainer model is appropriate for the current contributor count.

**Next (condition-gated):** Evaluate GitHub Organization migration only if two or more active contributors require distinct role-based permission boundaries that cannot be expressed through the current ruleset/CODEOWNERS model.

**Later:** If HUB_Optimus reaches external partnership, regulated use, or multi-team structure, a GitHub Organization enables fine-grained team permissions, audit logs, and SSO — but introduces governance overhead and an additional Microsoft/GitHub account layer.

**Decision criteria for migration:**
- More than one maintainer with distinct permission needs.
- A concrete integration that requires org-level webhooks, team-based CODEOWNERS, or org-level GitHub Apps.
- No migration without a separate scoped RFC.

### 5. How should Copilot/Codex/AI agents interact with the repo without becoming hidden authorities?

The `AGENTS.md` file defines the AI collaboration boundary explicitly:

> AI assistants may support HUB_Optimus as advisory operators, reviewers, drafters, and consistency checkers. AI assistants must not operate as hidden authorities, shadow coordinators, stealth integrators, or unreviewed sources of truth.

This RFC reinforces that boundary with the following operational rules:

- Every AI-assisted change must be visible in a GitHub PR with a traceable commit and a human-readable summary.
- Chat-only AI output is advisory until reflected in a versioned repository artifact (issue, PR, commit, or RFC).
- AI agents must not self-approve, self-merge, or bypass CODEOWNERS review gates.
- AI agents must not update `docs/context/AI_HANDOFF.md` outside the scoped issue or PR context.
- Copilot Coding Agent (cloud agent) changes must pass the same CI and governance gates as human contributors.
- No AI agent may introduce automation, workflows, or GitHub App integrations without an approved scoped issue.

These rules do not require settings changes. They are enforced through the PR review process, CODEOWNERS, and CI gates documented in the hardening backlog.

### 6. What Microsoft/GitHub ecosystem dependencies are acceptable, and what should remain portable?

See [Microsoft/GitHub Dependency-Risk Section](#microsoftgithub-dependency-risk) below.

### 7. What governance changes, if any, are needed before advanced automation or external collaboration?

Before any of the following are enabled — multi-contributor permissions, external collaboration, GitHub Apps, Copilot Workspace, scheduled automation — the following governance preconditions must be met:

1. Required status checks enforced through rulesets (currently `pending`; tracked in #1680–#1689).
2. CODEOWNERS enforcement enabled in active pull-request rules.
3. Admin/role bypass policy documented and minimized.
4. Overlapping rulesets consolidated or explicitly documented.
5. This RFC reviewed and accepted (or superseded by a follow-up RFC).

No advanced automation should be enabled until items 1–4 are resolved and verifiable.

---

## Adoption Table

The following table assesses GitHub capability areas against the Now / Next / Later / Avoid framework.

| Capability Area | Adoption | Rationale | Evidence |
|---|---|---|---|
| Branch rulesets protecting `main` | **Now (already active)** | Two active rulesets verified; non-fast-forward, deletion, signed commits, linear history enforced. | `GITHUB_SETTINGS_PROTECTION_CHECKLIST.md` — verified rows |
| Required status checks in rulesets | **Now** | Currently `pending`; CI, Kernel Guard, Link Check, PR Safety Check workflows exist but not required through rulesets. Enforce before new contributors join. | `GITHUB_SETTINGS_PROTECTION_CHECKLIST.md` — pending row; issues #1680–#1689 |
| CODEOWNERS enforcement | **Now** | `.github/CODEOWNERS` exists but `require_code_owner_review: false`. Enforce through rulesets before contributor growth. | `GITHUB_SETTINGS_PROTECTION_CHECKLIST.md` — pending row |
| Ruleset consolidation | **Now** | Two overlapping rulesets make merge-method policy ambiguous. Consolidate or document before new settings changes. | `GITHUB_SETTINGS_PROTECTION_CHECKLIST.md` — pending row |
| Bypass-actor policy documentation | **Now** | One ruleset has an undocumented `bypass_mode: always` actor. Document or remove. | `GITHUB_SETTINGS_PROTECTION_CHECKLIST.md` — pending row |
| GitHub Actions CI (existing) | **Now (already active)** | ci.yml, kernel-guard.yml, link-check.yml, pr-safety-check.yml are active. No new workflows needed. | `.github/workflows/` |
| Dependabot alerts | **Next** | Useful for dependency vulnerability detection. Enable alerts (read-only) without enabling auto-merge. No runtime risk. | No current evidence of Dependabot configuration; low-risk addition |
| Secret Scanning + Push Protection | **Next** | Prevents accidental credential commits. Enable for the repository. Does not change contributor workflow for legitimate commits. | No current evidence of secret scanning configuration |
| CodeQL (code scanning) | **Next (condition-gated)** | Relevant once Python or JavaScript code grows. Currently may produce low-value alerts for a documentation-heavy repo. Enable when the active codebase warrants it. | `hub_optimus_simulator.py`, `run_scenario.py`, `hub_optimus/` |
| GitHub Pages (already active) | **Now (already active)** | `pages.yml` deploys the project site. No change needed. | `.github/workflows/pages.yml` |
| GitHub Discussions | **Later** | Useful for open community questions without polluting the issue tracker. Enable only if external contributors are onboarded and a moderation policy exists. | Not currently used |
| GitHub Projects | **Later** | Issue triage and roadmap visibility. Enable only if the contributor count justifies the overhead. | Not currently used |
| GitHub Releases + provenance | **Next** | Releases provide versioned artifact anchors. No attestation (SLSA) needed now; add release notes convention in a scoped issue. | No release tag evidence in current review |
| Copilot Coding Agent | **Now (governed)** | Already in use with `AGENTS.md` visibility rules and `docs/context/AI_HANDOFF.md`. No new capability needed; enforce existing boundary rules. | `AGENTS.md`, `docs/context/AI_HANDOFF.md` |
| GitHub Organization migration | **Later (condition-gated)** | Evaluate only when multi-maintainer role boundaries require it. See RFC Answer 4. | Current user-owned model sufficient |
| Copilot Workspace / GitHub Copilot Extensions | **Avoid for now** | Insufficient governance visibility at this stage. May reintroduce hidden-authority risk. Revisit with a scoped RFC. | `AGENTS.md` AI collaboration boundary |
| GitHub Apps (third-party automation) | **Avoid for now** | Requires explicit permission grant and trust boundary decision. No current need. Open a scoped issue before evaluation. | No evidence of active GitHub App integrations |
| LLM-as-judge or AI scoring | **Avoid** | Explicitly rejected in `docs/context/AI_HANDOFF.md` and consistent with the hidden-authority prohibition. | `docs/context/AI_HANDOFF.md` — Do Not Do section |
| Automated merges (Dependabot auto-merge, merge queues without review) | **Avoid** | Bypasses CODEOWNERS and human review. Incompatible with current governance posture. | `AGENTS.md`, `GITHUB_SETTINGS_PROTECTION_CHECKLIST.md` |

---

## Explicit Rejections

The following capabilities are explicitly deferred or rejected at this time, with the reason recorded for traceability:

| Capability | Decision | Reason |
|---|---|---|
| GitHub Organization migration | Deferred | No multi-maintainer role boundary need yet. Revisit when two or more active contributors require distinct permissions. |
| GitHub Apps (third-party) | Deferred | Trust boundary not defined. Requires explicit scoped issue with permission analysis before evaluation. |
| Copilot Workspace / Copilot Extensions | Deferred | Governance visibility insufficient. Hidden-authority risk not mitigated at current maturity. |
| Automated merges (Dependabot or merge queues without review) | Rejected | Bypasses human review and CODEOWNERS enforcement. |
| LLM-as-judge or AI scoring metrics | Rejected | Permanently excluded. Violates hidden-authority and non-coercion principles. |
| SLSA provenance / artifact attestation | Deferred | Useful later; no distributable artifact at this stage. |
| GitHub Codespaces | Deferred | No current contributor need. Adds dependency surface without benefit. |
| Scheduled automation bots (repository health mutation) | Deferred | `repo_maintenance_bot.yml` exists as read-only health; no mutation automation authorized. |

---

## Microsoft/GitHub Dependency-Risk

### Acceptable dependencies (current)

The following GitHub/Microsoft dependencies are currently in use and considered acceptable given their governance visibility and reversibility:

- **GitHub Issues, PRs, and project state** — source of truth; no proprietary lock-in beyond standard git.
- **GitHub Actions** — CI automation through YAML-defined workflows; portable to alternative runners if needed.
- **GitHub Pages** — static site hosting; content is standard markdown/HTML; portable.
- **GitHub branch rulesets** — protect `main`; configuration is exportable and documentable.
- **GitHub CODEOWNERS** — standard file format; human-readable and portable.
- **GitHub Copilot Coding Agent** — currently used under `AGENTS.md` governance rules; advisory only; no autonomous merge authority.

### Dependency risks

| Dependency | Risk | Mitigation |
|---|---|---|
| GitHub Actions (workflow compute) | Vendor lock-in for CI syntax and marketplace actions. | Keep workflows minimal; prefer portable scripts over marketplace actions. Document external action pins. |
| GitHub Copilot (AI agent) | Governance opacity if agent scope expands without visibility rules. | `AGENTS.md` boundary is the current mitigation. Review before any scope expansion. |
| GitHub Projects/Discussions | Data lock-in if heavily adopted. | Use only if the benefit justifies the migration cost; maintain GitHub Issues as the canonical tracker. |
| GitHub Organization migration | Adds a Microsoft-managed account layer; harder to migrate away. | Defer until concrete need. Document decision criteria in a separate RFC before migrating. |
| GitHub-specific API features | Custom APIs (rulesets, required checks) may not be portable to other git platforms. | Document all settings in repo files (`GITHUB_SETTINGS_PROTECTION_CHECKLIST.md`). Keep git history and docs portable. |
| Microsoft ecosystem convergence | GitHub, Azure, Copilot, and VS Code integration may create bundled-service pressure. | Evaluate each integration separately through a scoped issue. No bundled adoption. |

### What must remain portable

The following must remain portable regardless of GitHub platform evolution:

- All scenario content, governance docs, and RFC documents (plain markdown).
- The git repository history.
- The simulator Python code.
- Benchmark fixtures and scenario schemas.
- The CI logic (extractable from workflow YAML into standalone scripts).

---

## Contributor Safety

### External contributor pickup

Before accepting external contributors:

1. Required status checks and CODEOWNERS enforcement must be active (currently `pending`).
2. A contributor guide must be visible and link to `AGENTS.md` AI collaboration rules.
3. The bypass-actor policy must be documented and minimized.
4. A PR template should be present or referenced in `CONTRIBUTING.md`.

### Permission model

The current model is:

- `@Voxterrae` has write access and ruleset bypass for `main`.
- No other collaborators are documented in current evidence.
- CODEOWNERS requires `@Voxterrae` review for all protected paths.

Before adding contributors:

- Define the minimum permission level needed (read, triage, write).
- Do not grant write access without a scoped issue documenting the rationale.
- Do not grant ruleset bypass to any contributor without explicit governance review.

### AI agent contributor safety

AI agents (including Copilot Coding Agent) must:

- operate through PRs with human-readable summaries;
- not self-approve or self-merge;
- not commit to `main` directly;
- not modify governance documents without the scoped issue explicitly authorizing it;
- not override CODEOWNERS review gates;
- update `docs/context/AI_HANDOFF.md` only when the scoped issue or PR changes operational handoff state.

These rules are currently enforced through the review process. Enforcement through required status checks and CODEOWNERS review enforcement (both currently `pending`) will make these rules structurally guaranteed rather than process-dependent.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Scope creep from this RFC | Medium | Medium | This RFC is planning-only. All follow-up requires a separate scoped issue. |
| Settings drift before hardening issues are resolved | Medium | High | Issues #1680–#1689 are the immediate execution backlog. This RFC adds no new items until those are resolved. |
| Hidden-authority introduction via AI agents | Low (currently) | High | `AGENTS.md` and `AI_HANDOFF.md` define the boundary. Required status checks + CODEOWNERS enforcement will structurally reinforce it. |
| Dependency lock-in from accelerated GitHub feature adoption | Low (currently) | Medium | Explicit Rejections table and deferred capabilities prevent premature adoption. |
| RFC becoming authoritative without review | Low | Medium | This RFC is Draft status. It must be reviewed and linked from the closing issue before being treated as accepted policy. |

---

## Validation

This RFC is considered validated when:

1. It has been reviewed and accepted in a GitHub PR that closes issue #1690.
2. All GitHub capability claims have been verified against current repository files and official GitHub documentation.
3. The four `pending` items in `GITHUB_SETTINGS_PROTECTION_CHECKLIST.md` remain tracked in the execution backlog.
4. No implementation action has been taken as a result of this RFC alone.

---

## Follow-up issues (candidates only)

The following are candidates for separate scoped issues after this RFC is accepted. No follow-up is authorized by this RFC alone.

1. Enforce required status checks through rulesets (from `pending` items).
2. Enable `require_code_owner_review` in active pull-request rules.
3. Document or remove the `bypass_mode: always` actor from active ruleset.
4. Consolidate or explicitly document overlapping branch rulesets.
5. Enable Dependabot alerts (alerts only; no auto-merge).
6. Enable Secret Scanning and Push Protection.
7. Add a GitHub release notes convention.
8. Evaluate CodeQL when Python codebase warrants it.
9. Evaluate GitHub Discussions when external contributors are onboarded.
10. Evaluate GitHub Organization migration against documented decision criteria.

---

## Future work

Possible follow-up work must be opened as separate GitHub issues after this RFC is reviewed.

No follow-up is authorized by this RFC alone.
