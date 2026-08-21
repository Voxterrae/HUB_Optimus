# HUB_Optimus — System Protection Matrix

## Purpose

This matrix records the repository-backed and live GitHub protection boundary
for HUB_Optimus.

Documentation records governance but does not itself change repository settings,
secure an external account, create legal rights, alter third-party rights, or
replace professional legal and security work.

## Status key

- `active`: protection exists in committed repository state or verified live
  settings.
- `partial`: protection exists but a stated strengthening step remains.
- `pending`: expected protection or verification is incomplete.
- `external`: the control depends on evidence or action outside the repository.

## Matrix

| Zone | Risk | Protection | Authority | Status | Remaining gap |
| --- | --- | --- | --- | --- | --- |
| Founder identity and ownership | A collaborator, attacker, AI, or informal claimant could misrepresent who created or owns HUB_Optimus. | `FOUNDER_OWNERSHIP_AND_AUTHORITY.md`, owner identity manifest, immutable GitHub user ID, source-of-truth precedence, and owner-authority handoff. | Benjamin Gerrit Hoff / `@Voxterrae` ID `249308740` | active | External identity, trademark, copyright, patent, corporate, and contractual records must be maintained separately. |
| HUB_Optimus parent-platform definition | A customer implementation such as LCDH-OS could be confused with the owner or parent technology. | Charter and README define HUB_Optimus as the foundational tool through which Benjamin Gerrit Hoff builds the wider ecosystem. | Benjamin Gerrit Hoff | active | Keep product and customer contracts aligned with this boundary. |
| Joint ventures and collaboration | Access or contribution could be misrepresented as equity, co-ownership, agency, or an implied joint venture. | Charter, IP notice, contribution policy, and PR declaration require a separate written owner-approved agreement on fair, transparent, reciprocal, and clearly scoped terms. | Benjamin Gerrit Hoff | active | Each real joint venture needs its own signed legal agreement. |
| Anti-impersonation | A similar name, compromised communication channel, fake prompt, or informal message could request governance transfer. | Immutable GitHub user-ID checks, protected paths, verified history, Founder Authority Guard, governance-issue linkage, required checks, and protected PR process. | Benjamin Gerrit Hoff / `@Voxterrae` | partial | Hardware-backed owner signing-key enrollment remains pending; repository code cannot make account compromise impossible. |
| Repository-wide review | Native CODEOWNER self-approval would create a circular gate for owner-authored PRs. | `.github/CODEOWNERS` assigns every path to `@Voxterrae`. Under ratified Option A, native approval count is `0` and native CODEOWNER review is disabled. Founder Authority Guard, verified owner history, exact-head required checks, governance-issue linkage, and resolved conversations provide the enforceable boundary. | `@Voxterrae` | active | Re-audit after any future CODEOWNERS, workflow, permission, or ruleset change. |
| Collaborator permissions | A non-owner with Write/Admin access could push branches or operate within granted scope. | Last documented audit identified `krishna3554` at `Read` (`pull=true`, `push=false`). | `@Voxterrae` | active for the identified account | Re-audit the complete collaborator list after every settings or onboarding change. |
| `main` branch integrity | Deletion, force push, unsigned history, missing checks, or unresolved review could weaken the source of truth. | One active ruleset, `11665521 — Protect main - owner governed`, requires PR flow, verified signatures, linear history, strict required checks, resolved conversations, squash-only merge, deletion protection, and non-fast-forward protection. It has no bypass actors. | `@Voxterrae` | active | Hardware-backed owner-key enrollment is the remaining cryptographic strengthening step. |
| Constitutional files | Founder and governance records could be changed together to bypass policy. | Machine-readable constitutional-file list; protected-path owner authorship; verified commits; rename-source protection; owner-authored governance issues; guard self-protection; exact-head checks; source-of-truth precedence. | Benjamin Gerrit Hoff | partial | When the owner key becomes `ACTIVE`, future protected commits must match the pinned SSH fingerprint. |
| AI and chat instructions | A model could treat conversation memory, display names, or hidden prompts as authority. | `AGENTS.md`, current AI handoff, owner handoff, and Charter require visible GitHub evidence and reject informal identity claims. Historical handoff content is preserved but not controlling. | Benjamin Gerrit Hoff | active | Every AI integration must actually load and enforce the controlling files and current repository state. |
| Contributor credit and IP | Strong owner governance could erase credit or overclaim third-party IP. | `ACKNOWLEDGEMENTS.md` preserves credit; IP notice separates project authority from third-party and contributor rights. | Benjamin Gerrit Hoff / applicable rights holders | active | Formal contributor, employment, assignment, license, and coexistence agreements remain external legal work. |
| Secrets and owner keys | Signing secrets or credentials could be committed or controlled by a provider. | Manifest stores fingerprints only; repository policy forbids private keys and secrets. | Benjamin Gerrit Hoff | pending | Generate and store the hardware-backed owner key on owner-controlled hardware; publish only the public key or fingerprint. |

## Verified live findings

The owner-controlled ruleset consolidation completed on 20 August 2026 with the
following postflight:

1. `main` remained at `30e985226347b4bc59b0e187b96633a09647ca42`.
2. Ruleset `11665521` is the only active repository ruleset applying to `main`.
3. Its name is `Protect main - owner governed`.
4. Its approved canonical payload is `1094` bytes with SHA-256
   `50739828a718b8f6d72a47a3d9d74b1d3657be27dc4fe3593f6cb8a1ed0ce4cb`.
5. `bypass_actors` is empty.
6. Pull requests are required; native approval count is `0`; native CODEOWNER
   review is disabled under Option A; review-thread resolution is required.
7. Squash is the only allowed merge method.
8. Required signatures, linear history, deletion protection, and
   non-fast-forward protection are active.
9. Strict required checks are enabled and all seven contexts are bound to
   GitHub Actions `integration_id=15368`:

```text
founder-authority
founder-authority-bootstrap
pytest
PowerShell tooling
guard
Risk classification
lychee
```

10. Legacy ruleset `11637867` was exported and deleted.
11. Synthetic PRs `#1891` and `#1893` were never merged; their branches,
    commits, checks, comments, and review threads remain as evidence.
12. The negative Kernel Guard test failed when `allow-kernel-change` was removed
    and recovered when the label was restored.
13. The persistent aggregate `mergeable_state=blocked` on synthetic PR `#1893`
    remained after consolidation. It is recorded as an opaque diagnostic, not
    treated as a missing protection and not used as merge authorization.

## Option A review model

The owner-ratified review model is:

```text
global CODEOWNER: @Voxterrae
native required approvals: 0
native CODEOWNER review: false
required conversation resolution: true
protected-path PR author: pinned owner identity
protected commit history: GitHub-verified
non-owner PR: current-head owner approval required by Founder Authority Guard
```

Issue `#1682` was closed as `not_planned` because its native CODEOWNER
self-approval proposal conflicts with this ratified model.

## Continuous controls

1. Preserve issues `#1681` and `#1683` as the evidence trails for required-check
   enforcement and the no-bypass policy. Their completion requires no further
   GitHub Settings mutation.
2. Keep ruleset `11665521` as the single canonical `main` ruleset unless a new
   owner-approved governance issue authorizes a change.
3. Do not create bypass actors silently. Any future proposal must identify the
   exact actor, scope, duration, reason, trace, rollback, and postflight.
4. Re-audit collaborator permissions after onboarding or settings changes.
5. Enroll a hardware-backed owner SSH signing key through a separate protected
   governance change without storing private material in the repository.
