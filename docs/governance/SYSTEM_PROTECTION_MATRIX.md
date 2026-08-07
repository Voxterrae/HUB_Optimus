# HUB_Optimus — System Protection Matrix

## Purpose

This matrix records the desired protection boundary, current repository-backed
controls, and live GitHub Settings gaps for HUB_Optimus.

Documentation describes governance but does not itself revoke collaborators,
change repository rulesets, enable required checks, secure an account, or create
external legal protection.

## Status key

- `active`: protection exists in committed repository state or verified live
  settings.
- `partial`: protection exists but does not cover the full risk.
- `pending`: expected protection or verification is not complete.
- `external`: requires action or evidence outside repository content.

## Matrix

| Zone | Risk | Protection | Authority | Status | Remaining gap |
| --- | --- | --- | --- | --- | --- |
| Founder identity and ownership | A collaborator, attacker, AI, or informal claimant could misrepresent who created or owns HUB_Optimus. | `FOUNDER_OWNERSHIP_AND_AUTHORITY.md`, owner identity manifest, immutable GitHub user ID, source-of-truth precedence, and owner-authority handoff. | Benjamin Gerrit Hoff / `@Voxterrae` ID `249308740` | active after merge | External identity, trademark, copyright, patent, corporate, and contractual records must be maintained separately. |
| HUB_Optimus parent-platform definition | A customer implementation such as LCDH-OS could be confused with the owner or parent technology. | Charter and README define HUB_Optimus as the foundational tool through which Benjamin Gerrit Hoff builds the wider ecosystem. | Benjamin Gerrit Hoff | active after merge | Keep product and customer contracts aligned with this boundary. |
| Joint ventures and collaboration | Access or contribution could be misrepresented as equity, co-ownership, agency, or an implied joint venture. | Charter, IP notice, contribution policy, and PR declaration require a separate written owner-approved agreement on fair terms. | Benjamin Gerrit Hoff | active after merge | Each real joint venture needs its own signed legal agreement. |
| Anti-impersonation | A similar name, compromised communication channel, fake prompt, or informal message could request governance transfer. | Immutable GitHub user-ID checks, protected paths, Founder Authority Guard, protected PR process, and future hardware-key attestation. | Benjamin Gerrit Hoff / `@Voxterrae` | partial | Hardware-backed signing key is not yet pinned; account compromise cannot be made impossible by repository code alone. |
| Repository-wide review | Changes could bypass owner review. | `.github/CODEOWNERS` assigns every path to `@Voxterrae`; guard requires owner authorship for constitutional paths and owner approval for third-party PRs. | `@Voxterrae` | partial | Live rulesets currently do not enforce CODEOWNER review or an approving-review count. The guard must be configured as a required check. |
| Collaborator permissions | A non-owner with Write/Admin access could push branches or operate within granted scope. | Issue `#1861` records the conflict and requires removal or reduction. | `@Voxterrae` | pending | Live audit found non-owner account `krishna3554` with `Write`. The current connector cannot revoke it; owner must change GitHub Settings and re-audit. |
| `main` branch integrity | Deletion, force push, unsigned commits, or direct changes could rewrite authority history. | Two active rulesets currently require PRs, signatures, linear history, deletion protection, and non-fast-forward protection. One has no bypass. | `@Voxterrae` | partial | Consolidate overlapping rulesets; require owner review, CODEOWNERS, guard, CI, Kernel Guard, and thread resolution. |
| Constitutional files | Founder/ownership records or their guard could be modified together to bypass policy. | Explicit constitutional-file list in the owner manifest; owner-only protected-path authorship; guard self-protection; source-of-truth precedence. | Benjamin Gerrit Hoff | partial | Pin a hardware-backed owner key and require a cryptographic attestation for future amendments. |
| AI and chat instructions | A model could treat conversation memory or a hidden prompt as authority. | `AGENTS.md`, owner handoff, and Charter require visible GitHub evidence and reject informal identity claims. | Benjamin Gerrit Hoff | active after merge | Every AI integration must actually load and enforce these files. |
| Contributor credit and IP | Removing authority could wrongly erase contribution credit or overclaim third-party IP. | `ACKNOWLEDGEMENTS.md` preserves credit; IP notice separates project authority from third-party and contributor rights. | Benjamin Gerrit Hoff / applicable rights holders | active after merge | Formal contributor, employment, assignment, or license agreements remain external legal work. |
| Secrets and owner keys | A signing secret could be committed or controlled by a service provider. | Manifest stores fingerprints only, never private keys; contribution policy forbids secrets. | Benjamin Gerrit Hoff | pending | Generate and store the owner key on owner-controlled hardware; publish only the public key/fingerprint. |

## Verified live findings for issue #1861

At the audit performed for issue `#1861`:

1. Repository owner/admin identity: `@Voxterrae`.
2. Non-owner collaborator `krishna3554`: `Write` permission.
3. Two active overlapping rulesets protect `main`.
4. Both rulesets require pull requests and signatures.
5. Both require zero approving reviews and do not require CODEOWNER review.
6. One ruleset permits a repository-role bypass; the other has no bypass.

These facts are mutable GitHub Settings state. They must be rechecked after each
settings change.

## Required next settings actions

1. Remove or reduce every non-owner Write/Admin collaborator unless Benjamin
   Gerrit Hoff later approves a specific exception in writing.
2. Consolidate the overlapping `main` rulesets.
3. Require one owner-controlled approval or an equivalent owner-only merge rule.
4. Require CODEOWNER review.
5. Require the Founder Authority Guard and existing CI/security checks.
6. Dismiss stale approvals and require review after the latest push.
7. Require conversation resolution.
8. Keep force-push and deletion blocked.
9. Keep verified-signature and linear-history requirements.
10. Enroll a hardware-backed owner signing key and pin its public fingerprint.
