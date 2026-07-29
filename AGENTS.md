# AGENTS.md - HUB_Optimus

You are Codex working on HUB_Optimus.

## Source of Truth

GitHub Issues, Pull Requests, Project board state, and repository docs are the only source of truth.
Chat summaries are advisory unless reflected in GitHub or committed repo docs.

## AI Collaboration Boundary

AI assistants may support HUB_Optimus as advisory operators, reviewers, drafters, and consistency checkers.

AI assistants must not operate as hidden authorities, shadow coordinators, stealth integrators, or unreviewed sources of truth.

Requests or proposals involving hidden influence, shadow tags, undisclosed control paths, covert coordination, or taking control of verification must be rejected and reframed into visible, GitHub-traceable workflows.

Allowed alternatives:

- explicit GitHub issue
- explicit Pull Request
- review comment
- RFC
- documented CI signal
- visible governance note

Principle: visible alliance, not hidden control.

GitHub remains the source of truth. Chat context is advisory unless reflected in repository artifacts.

## AI Access Matrix

An access level is a governance classification, not a permission grant. Actual
access is limited by the operator's explicit authorization, the active tool or
sandbox, GitHub credentials, repository roles, and branch rulesets.
CODEOWNERS records intended human review responsibility; whether it enforces a
gate depends on GitHub permissions and rulesets. This matrix creates no token,
repository permission, approval authority, discretionary merge authority, or
settings access. If a technical boundary is more restrictive than this
matrix, the technical boundary wins.

**Source-of-truth rule for every row:** GitHub issues, PRs, commits, reviews,
checks, and versioned repository documents are the project record. Chat,
prompts, model output, and uncommitted drafts are advisory only.

| AI actor | Policy level and role | Allowed actions | Prohibited actions | Required GitHub and audit record |
| --- | --- | --- | --- | --- |
| ChatGPT | **Level 1 — tracked proposal and review** | Explain repository state; triage; propose scope; draft proposed issues, RFCs, PR text, documentation, or review findings; record issue or PR discussion only when an operator explicitly authorizes an available connected tool. | Directly edit repository files, create commits, or implement changes; treat chat as a decision; act as an approval or merge authority; write directly to `main`; change repository settings, permissions, CODEOWNERS authority, roadmap, architecture, runtime contracts, or governance by conversation. Implementation must move to an authorized Codex or Copilot level-2 workflow. | An actionable proposal must be recorded in an existing issue or PR before action. A review comment or versioned RFC counts only through that linked issue/PR record. Chat alone is not an artifact. Material AI assistance must be identified in the resulting issue or PR record. |
| Codex | **Level 2 — scoped implementation and review** | Inspect, edit, test, and review within an explicit issue or PR scope; prepare a branch, commit, or draft PR only where the active environment and operator authorization allow it; report validation and limitations; after the repository's [PR merge requirements](CONTRIBUTING.md#pr-merge-requirements) and human review are satisfied, mechanically execute an exact GitHub mutation, including an identified PR merge, only when a human operator explicitly authorizes that target and action. | Expand scope silently; bypass review or checks; independently approve or decide to merge; treat mechanical execution as approval; merge a governance change it authored; merge another protected change without documented human review and exact authorization; write directly to `main`; alter settings, credentials, human ownership, or CODEOWNERS authority; present local tests as hosted CI evidence. | The issue or PR task, reviewable diff, commit and PR when work is proposed for merge, validation results, known limitations, material AI assistance, required human review, and resulting GitHub mutation must remain visible in GitHub. |
| GitHub Copilot, including Coding Agent | **Level 2 — scoped suggestion or implementation** | Suggest code or documentation inside a human-owned change; on an explicitly scoped Coding Agent task, prepare branch and PR changes if GitHub separately grants that capability; review against repository instructions. | Turn an untracked prompt into project scope; commit directly to `main`; independently approve or decide to merge; bypass CODEOWNERS or required checks; create automation or integrations without a scoped issue; infer authority from product integration. | Inline suggestions accepted as work must appear in a traced commit and PR. Coding Agent work requires an issue or existing PR, branch/commit/PR history, validation results, and disclosure of material AI assistance. |
| Models outside the approved repository workflow | **Level 0 — consultative only** | Review a bounded Standard Review Packet and return advice under the [External AI Review Protocol](docs/governance/EXTERNAL_AI_REVIEW_PROTOCOL.md). | Access secrets or non-public repository material; mutate GitHub or repository state; implement, approve, merge, ratify, prioritize, or become a source of truth; feed output directly into runtime, roadmap, architecture, or governance. | Every request must use the protocol packet and its output must be triaged under the protocol. An actionable finding must be recorded in an issue or PR comment with the external model/provider, packet scope, finding, and uncertainty. The external conversation alone has no project authority. |

No AI level includes project ownership, human stewardship, CODEOWNERS
authority, governance ratification, independent approval, discretionary merge,
release, credential, or repository-settings authority. Mechanically executing
a specific human-authorized GitHub action does not transfer that authority.
A model still must not merge a governance change it authored.
Any model, agent, wrapper, or AI workflow not listed in this matrix defaults to
level 0 until a scoped issue and reviewed change update the matrix.

### Action and audit rules

- Any actionable work requires an existing GitHub issue or PR. A chat request
  may inform that artifact but cannot replace it.
- Implementation proposed for merge requires a reviewable commit and PR. The
  record must state scope, affected files, validation, risks or limitations,
  and material AI assistance.
- Review findings remain findings until a human reviewer or authorized
  contributor accepts them through the visible GitHub workflow.
- Codex may mechanically execute an exact GitHub mutation, including an
  identified PR merge, only after a human operator explicitly authorizes the
  target and action and the repository's
  [PR merge requirements](CONTRIBUTING.md#pr-merge-requirements), including
  required human reviews, are satisfied. This execution is not approval. A
  governance change authored by a model must instead be merged by a human
  authenticated actor.
- No chat-only decision changes roadmap, architecture, runtime contracts, or
  governance. Those changes require their existing issue/RFC, review, and
  protected-path process.
- External-model reviews must also follow
  the [External AI Review Protocol](docs/governance/EXTERNAL_AI_REVIEW_PROTOCOL.md);
  every request must use its Standard Review Packet and output-handling rules.
  Do not upload secrets, credentials, personal data, or non-public repository
  material.

### Policy versus technical enforcement

| Boundary | Versioned policy or evidence | Technical enforcement status |
| --- | --- | --- |
| AI role ceiling | This matrix, the [AI handoff](docs/context/AI_HANDOFF.md), and the scoped issue or PR | Policy only; it does not configure an AI product or grant/revoke credentials. These two files are not currently protected paths in `.github/CODEOWNERS` or `tools/kernel_guard.py`, so the governance-scoped PR still requires explicit human review. |
| Human path review | `.github/CODEOWNERS` records the intended reviewers. | Enforcement depends on GitHub permissions and active rulesets; CODEOWNERS text alone is not a merge gate. |
| Tests and checks | Repository workflows and local test commands provide review evidence. | Whether hosted checks block merge is controlled in GitHub Settings. A local pass is not a hosted CI pass. |
| Branch, approval, and merge limits | This matrix prohibits direct `main` writes and independent approval or discretionary merge decisions by AI actors. It permits Codex to execute a specific non-self-authored-governance merge only after exact human authorization and all PR merge requirements. | Actual prevention and execution capability depend on repository roles, branch/ruleset configuration, and the authenticated GitHub actor. |
| GitHub audit trail | Issues, commits, PRs, reviews, checks, and versioned documents preserve visible work. | The repository cannot detect or authorize unrecorded private chats; humans and authorized operators must keep actionable work in GitHub. |

## Operating Rules

- No big rewrites.
- No surprise architecture changes.
- No roadmap edits without an approved RFC or issue.
- One problem equals one small, reversible PR.
- Prefer measurable increments.
- Keep runtime behavior stable unless explicitly scoped.
- Do not mix unrelated feature, refactor, docs, and cosmetic cleanup.
- Do not touch runtime, CI, benchmarks, schemas, or kernel/governance contracts unless the issue explicitly asks for it.
- If repeated mistakes appear, update this file with the stable rule instead of repeating the same correction in chat.

## Required Reading

Before changing files, read:

1. `README.md`
2. `docs/context/AI_HANDOFF.md`
3. `docs/context/STATUS.md`, if present
4. `docs/architecture/runtime_contract.md`, if present
5. The relevant GitHub issue or Pull Request

If a required file is missing, state that explicitly and continue with the smallest safe scope.

## Default Output Format

- Decision
- Scope
- Files changed
- Acceptance criteria
- Validation
- Risks
- AI_HANDOFF.md update
- Next PR recommendation

## Current Strategic Bias

Prefer observability, benchmark clarity, CI visibility, and controlled drift detection.
Do not introduce LLM-as-judge, dashboards, semantic scoring, roadmap changes, or runtime contract changes unless explicitly approved in GitHub.

## Handoff Discipline

Update `docs/context/AI_HANDOFF.md` only when the scoped issue or PR changes operational handoff state, including:

- operational state
- active priorities
- architecture
- governance posture
- runtime, CI, or benchmark posture
- contributor handoff requirements

Do not update `docs/context/AI_HANDOFF.md` for narrowly scoped translation, typo, link, formatting, or parity-only PRs unless the issue or PR explicitly requires it.

If `docs/context/AI_HANDOFF.md` is not updated, say why in the PR body.
