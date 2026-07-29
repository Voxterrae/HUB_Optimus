# HUB_Optimus source-of-truth hierarchy

This hierarchy defines which evidence wins when two project artifacts appear to
describe the same state. It does not make every fact available from one file.
The question must first be classified, and the narrowest direct evidence below
must be used.

## Precedence

1. **GitHub `main` and live GitHub records.** The immutable commit on
   `Voxterrae/HUB_Optimus` is authoritative for the repository tree that it
   contains. Live Issues, Pull Requests, Checks, Releases, Project state, and
   repository settings are authoritative only for their own current GitHub
   state. A checkout cannot certify those mutable external facts.
2. **Canonical domain contracts inside that commit.** Governance text under
   `docs/governance/` governs project rules. For executable behavior, the
   applicable schema, source, and
   [`runtime_contract.md`](../architecture/runtime_contract.md) are read
   together with the tests that exercise the claimed boundary. A passing test
   proves only its asserted behavior.
3. **[`STATUS.md`](STATUS.md) for canonical-language and parity policy.**
   `STATUS.md` resolves which language or surface is canonical. It does not
   override executable behavior, governance, or live GitHub state.
4. **[`AI_HANDOFF.md`](AI_HANDOFF.md) for operational handoff.** The handoff
   summarizes merged boundaries and current contributor constraints. It must
   cite GitHub or repository evidence and cannot turn chat, a proposal, or an
   external deployment into repository truth.
5. **Versioned capability evidence.** The
   [capability ledger](../architecture/capability_status.md) and its
   [machine-readable evidence snapshot](../architecture/capability_evidence.v1.json)
   are derived views at one explicit commit. They never certify later PR
   state, deployment, repository settings, legal conclusions, or professional
   review.
6. **Overview, onboarding, and historical records.** Navigation and overview
   documents summarize the sources above. Historical checkpoints record what
   was said at an earlier time and are never current operational authority.

## Conflict rule

When claims conflict, use the higher applicable source and retain the narrower
claim. Mark mutable GitHub, deployment, infrastructure, repository-settings,
release, and third-party facts as external until inspected directly at a
stated time. Mark a capability unresolved when the baseline has no direct
evidence; absence of evidence is not evidence of a positive capability.

Chat history, model output, generated prose, file presence, and a green test
outside its asserted boundary do not outrank this hierarchy.
