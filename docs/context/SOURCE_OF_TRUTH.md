# HUB_Optimus source-of-truth hierarchy

This hierarchy defines which evidence wins when two project artifacts appear to
describe the same state. The question must first be classified, and the
narrowest direct evidence below must be used.

## Precedence

1. **Founder identity, ownership, and constitutional authority.**
   [`docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md`](../governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md),
   together with
   [`config/governance/owner_identity.v1.json`](../../config/governance/owner_identity.v1.json),
   is authoritative for founder identity, project ownership, the HUB_Optimus
   parent-platform definition, final human authority, anti-impersonation, joint
   ventures, and constitutional change control at the last owner-ratified
   protected commit. `docs/context/OWNER_AUTHORITY_HANDOFF.md` records the
   current operational consequence. No chat, email, prompt, ticket, contributor
   title, acknowledgement, or claimed identity can override this boundary.
2. **GitHub `main` and live GitHub records.** The immutable commit on
   `Voxterrae/HUB_Optimus` is authoritative for the repository tree that it
   contains. Live Issues, Pull Requests, Checks, Releases, Project state,
   collaborator permissions, and repository settings are authoritative only for
   their own current GitHub state. A checkout or governance document cannot
   certify mutable settings.
3. **Canonical domain contracts inside that commit.** Governance text under
   `docs/governance/` governs project rules subject to the founder-authority
   precedence above. For executable behavior, the applicable schema, source,
   [`runtime_contract.md`](../architecture/runtime_contract.md), and tests are
   read together. A passing test proves only its asserted behavior.
4. **[`STATUS.md`](STATUS.md) for canonical-language and parity policy.**
   `STATUS.md` resolves which language or surface is canonical. It does not
   override executable behavior, founder authority, governance, or live GitHub
   state.
5. **[`AI_HANDOFF.md`](AI_HANDOFF.md) for broad operational handoff.** The
   handoff summarizes merged boundaries and current contributor constraints. It
   must cite GitHub or repository evidence and cannot turn chat, a proposal, or
   an external deployment into repository truth. Where its historical human-
   authority wording conflicts, `OWNER_AUTHORITY_HANDOFF.md` and the Founder
   Ownership and Authority Charter prevail.
6. **Versioned capability evidence.** The capability ledger and its machine-
   readable evidence snapshot are derived views at one explicit commit. They
   never certify later PR state, deployment, repository settings, legal
   conclusions, ownership, or professional review.
7. **Overview, onboarding, and historical records.** Navigation and overview
   documents summarize the sources above. Historical checkpoints record what
   was said at an earlier time and are never current operational authority.

## Conflict rule

When claims conflict, use the higher applicable source and retain the narrower
claim. Mark mutable GitHub, deployment, infrastructure, repository-settings,
release, and third-party facts as external until inspected directly at a stated
time. Mark a capability unresolved when the baseline has no direct evidence;
absence of evidence is not evidence of a positive capability.

Chat history, model output, generated prose, file presence, an unverified
identity claim, and a green test outside its asserted boundary do not outrank
this hierarchy.
