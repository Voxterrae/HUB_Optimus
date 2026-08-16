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
- `active after merge`: protection is present in this reviewed proposal but is
  not active on `main` until the proposal is owner-ratified and merged.
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
| Repository-wide review | Native CODEOWNER approval would create a circular gate because GitHub does not allow the sole CODEOWNER to approve an owner-authored PR. | `.github/CODEOWNERS` assigns every path to `@Voxterrae`. Under owner-approved Option A, native required-approval count and native CODEOWNER-review enforcement remain disabled. The Founder Authority Guard instead requires owner-authored verified history for protected paths and current-head owner approval for non-owner PRs. | `@Voxterrae` | partial | Configure the exact-head Founder Authority Guard and existing CI/security checks as required after the workflow is active on `main`; require conversation resolution. |
| Collaborator permissions | A non-owner with Write/Admin access could push branches or operate within granted scope. | The live re-audit on 15 August 2026 shows `krishna3554` at `Read` (`pull=true`, `push=false`). | `@Voxterrae` | active for the identified account | Re-audit the complete collaborator list after every settings change; this row does not claim that documentation itself controls permissions. |
| `main` branch integrity | Deletion, force push, unsigned commits, or direct changes could rewrite authority history. | Two active rulesets currently require pull requests, signatures, linear history, deletion protection, and non-fast-forward protection. One has no bypass. | `@Voxterrae` | partial | Consolidate the overlapping rulesets; require the exact-head Founder Authority Guard, CI, Kernel Guard, PR Safety Check, Link Check, and thread resolution. Do not add a native CODEOWNER self-approval gate. |
| Constitutional files | Founder/ownership records or their guard could be modified together to bypass policy. | Explicit constitutional-file list in the owner manifest; owner-only protected-path PR and commit identities; rename-source protection; verified governance issue linkage; guard self-protection; source-of-truth precedence. | Benjamin Gerrit Hoff | partial | Pin a hardware-backed owner key and require its registered fingerprint for future protected commits. |
| AI and chat instructions | A model could treat conversation memory or a hidden prompt as authority. | `AGENTS.md`, current AI handoff, owner handoff, and Charter require visible GitHub evidence and reject informal identity claims. The pre-#1862 handoff is preserved as history, not current authority. | Benjamin Gerrit Hoff | active after merge | Every AI integration must actually load and enforce the current controlling files. |
| Contributor credit and IP | Removing authority could wrongly erase contribution credit or overclaim third-party IP. | `ACKNOWLEDGEMENTS.md` preserves credit; IP notice separates project authority from third-party and contributor rights. | Benjamin Gerrit Hoff / applicable rights holders | active after merge | Formal contributor, employment, assignment, or license agreements remain external legal work. |
| Secrets and owner keys | A signing secret could be committed or controlled by a service provider. | Manifest stores fingerprints only, never private keys; contribution policy forbids secrets. | Benjamin Gerrit Hoff | pending | Generate and store the owner key on owner-controlled hardware; publish only the public key or fingerprint. |

## Verified live findings for issue #1861

At the re-audit performed on 15 August 2026:

1. Repository owner/admin identity: `@Voxterrae`.
2. The previously identified collaborator `krishna3554` has `Read`, not `Write`:
   `pull=true`, `push=false`, `maintain=false`, and `admin=false`.
3. Two active overlapping rulesets protect `main`: `11637867` and `11665521`.
4. Both rulesets require pull requests and signatures.
5. Both currently require zero approving reviews, do not require CODEOWNER
   review, and do not require review-thread resolution.
6. Ruleset `11637867` permits a repository-role bypass; ruleset `11665521` has
   no bypass and permits only squash merges.

These facts are mutable GitHub Settings state. They must be rechecked after each
settings change. Under owner-approved Option A, zero native approvals and no
native CODEOWNER review are deliberate while `@Voxterrae` is the sole
CODEOWNER; the remaining gaps are the overlapping rulesets, the bypass in the
older ruleset, missing exact-head guard/CI requirements, and missing conversation
resolution.

## Required next settings actions

These actions are a later owner-interface gate and are not performed by PR
`#1862`:

1. Consolidate the overlapping `main` rulesets into one owner-controlled rule.
2. Keep native required-approval count and native CODEOWNER-review enforcement
   disabled while `@Voxterrae` is the sole CODEOWNER.
3. Require the trusted `Founder Authority Guard` check published against the
   exact current PR head.
4. Require CI, Kernel Guard, PR Safety Check, and Link Check.
5. Require conversation resolution.
6. Keep force-push and deletion blocked.
7. Keep verified-signature and linear-history requirements.
8. Remove the general repository-role bypass unless a later explicit owner
   decision defines a narrower emergency path.
9. Re-audit all collaborator permissions and preserve least privilege.
10. Enroll a hardware-backed owner SSH signing key and pin only its public
    fingerprint.
