# RFC: Constitutional Vocabulary and Amendment Mechanics

## Status

- **Draft / RFC only**
- **Not ratified**
- **Documentation only**
- **Tracks:** [issue #1751](https://github.com/Voxterrae/HUB_Optimus/issues/1751)
- **Date:** 2026-07-28

This RFC proposes vocabulary and amendment mechanics for human review. It does
not amend the Kernel, governance documents, runtime, schemas, CI, licensing,
repository settings, CODEOWNERS, or any current capability status.

Merging this file as `Draft` would publish a proposal only. It would not accept
the proposal, amend an existing constitutional document, appoint a Custodian,
or create authority. Explicit human ratification and separately reviewed
follow-up changes would be required before any part becomes normative.

## Decision requested

Human reviewers are asked to decide whether HUB_Optimus should:

1. reserve **Normative Kernel** for constitutional semantic invariants;
2. stop using unqualified `kernel` for the v1 method and Python simulator;
3. distinguish semantic invariants from technically unchangeable bytes;
4. distinguish legal/project control from normative legitimacy;
5. make constitutional review decidable from versioned GitHub records; and
6. require explicit human ratification, with no AI self-approval.

No decision is made by this Draft.

## Verified repository signal

The repository currently uses overlapping terms and incomplete decision rules.
This table records the textual signal; it does not make a legal conclusion.

| Versioned source | Current signal | Ambiguity to resolve |
| --- | --- | --- |
| [`docs/governance/KERNEL.md`](../governance/KERNEL.md) | Calls its principles immutable and non-negotiable, then permits amendment through Custodianship and Consensus. | Whether `immutable` means unchangeable bytes, stable meaning within a version, or amendable principles. |
| [`docs/governance/CUSTODIANSHIP.md`](../governance/CUSTODIANSHIP.md) and [`CONSENSUS_PROCESS.md`](../governance/CONSENSUS_PROCESS.md) | Require proposals, review, objections, consensus, Custodian approval, and language synchronization. | No current Custodian roster, eligibility rule, quorum, threshold, fixed review window, ratifier, deadlock rule, or emergency path is defined. |
| [`IP_NOTICE.md`](../../IP_NOTICE.md) and [`docs/governance/IP_NOTICE.md`](../governance/IP_NOTICE.md) | Say designated Kernel files may not be modified. | The governed exception described by the amendment documents is not stated. |
| [`CHARTER.md`](../governance/CHARTER.md), [`LEGITIMACY_MODEL.md`](../governance/LEGITIMACY_MODEL.md), and [`PROJECT_STEWARDSHIP.md`](../governance/PROJECT_STEWARDSHIP.md) | Reject unilateral normative authority while recording project ownership, administration, stewardship, and final human accountability. | Legal/project roles and procedural legitimacy are not explicitly separated. |
| [`docs/context/STATUS.md`](../context/STATUS.md), [`README.md`](../../README.md), [`KERNEL_CHARTER.md`](../../KERNEL_CHARTER.md), and [`runtime_contract.md`](../architecture/runtime_contract.md) | Use `kernel` for the canonical v1 method and for simulator code as well as governance. | Three different things appear to share one name. |
| [`semantic_engine/contracts/analysis_result.py`](../../semantic_engine/contracts/analysis_result.py), [`semantic_engine_cli.md`](../architecture/semantic_engine_cli.md), and [`site/operator/index.html`](../../site/operator/index.html) | Contain executable contracts, a minimal CLI, and a browser interface prototype. | Interfaces and contracts can be mistaken for constitutional authority or for the complete planned engine. |
| `docs/rfc/` | Contains Draft and planned capabilities. | A proposal can be mistaken for an accepted rule or implemented capability. |

## Scope

This RFC proposes:

- one candidate vocabulary;
- an operational meaning of `immutable`;
- one candidate relationship between ownership, stewardship, and legitimacy;
- reviewer eligibility and conflict rules;
- review classes and fixed windows;
- quorum and approval thresholds;
- objection, deadlock, ratification, emergency, rollback, versioning, and
  evidence-record mechanics; and
- a strict human/AI authority boundary.

## Out of scope

This RFC does not:

- edit or reinterpret an existing governance file as already amended;
- make legal findings, transfer ownership, or grant a license;
- appoint, remove, or recognize a Custodian;
- change current stewardship or CODEOWNERS assignments;
- change the canonical v1 method;
- change the simulator, Semantic Engine, Operator, API, schemas, tests,
  benchmarks, CI, hosting, or repository settings;
- declare an RFC accepted or a planned capability implemented; or
- authorize an AI system to approve, ratify, or merge governance work.

## Candidate vocabulary

If ratified, the following terms would be used consistently. File names do not
change merely because this vocabulary is proposed.

### 1. Normative Kernel

The **Normative Kernel** is the versioned set of constitutional semantic
invariants that defines what may be represented as HUB_Optimus. Its primary
current expression is [`docs/governance/KERNEL.md`](../governance/KERNEL.md),
read with the canonical governance documents that the
[Charter](../governance/CHARTER.md) incorporates.

The Normative Kernel is:

- normative meaning, not Python code;
- a constraint on compatible governance and implementation;
- non-executable;
- subject to the human amendment process proposed below; and
- unchanged unless a new ratified normative version says otherwise.

The phrase **Kernel document** should mean a file explicitly listed in a
ratified Kernel manifest. The current repository does not contain such a
manifest. This Draft does not create one or silently decide which files it
would include.

### 2. Canonical governance set

The **canonical governance set** is the English source set under
`docs/governance/` identified by the current
[Translation Policy](../governance/TRANSLATION_POLICY.md). It contains the
Normative Kernel's expression and the rules that interpret or apply it.

`Canonical` answers **which versioned source wins when mirrors differ**. It does
not mean that every sentence is a Kernel invariant, that the bytes cannot
change, or that a document has been legally validated.

### 3. Canonical v1 method

The **canonical v1 method** is the Spanish human-readable methodology identified
by [`docs/context/STATUS.md`](../context/STATUS.md), beginning with:

- [`01_base_declaracion.md`](../../v1_core/languages/es/01_base_declaracion.md);
- [`02_arquitectura_base.md`](../../v1_core/languages/es/02_arquitectura_base.md);
  and
- [`03_flujo_operativo.md`](../../v1_core/languages/es/03_flujo_operativo.md).

It describes the v1 analytical method and workflow. It is not the Normative
Kernel and is not executable merely because repository documentation has called
`v1_core/` an active kernel. Its Spanish canonical status is a source hierarchy
rule, not a claim of constitutional or legal immutability.

### 4. Scenario simulator runtime

The **scenario simulator runtime** is the executable prototype described by
[`runtime_contract.md`](../architecture/runtime_contract.md), principally:

- [`hub_optimus_simulator.py`](../../hub_optimus_simulator.py);
- [`run_scenario.py`](../../run_scenario.py); and
- [`scenario.schema.json`](../../scenario.schema.json).

It validates scenario inputs and produces the currently documented deterministic
result behavior. It is implementation, not constitutional text. References to
the simulator as a `kernel` should be read as **simulation core** until a
separate reviewed cleanup changes the existing wording.

### 5. Semantic Engine contracts

The **Semantic Engine contracts** are the implemented, versioned data shapes and
the minimal CLI behavior evidenced by
[`analysis_result.py`](../../semantic_engine/contracts/analysis_result.py) and
[`semantic_engine_cli.md`](../architecture/semantic_engine_cli.md).

They structure claims, evidence, analysis results, decision traces, and audit
events. They do not by themselves perform truth adjudication, complex
evaluation, hidden scoring, or governance ratification. The broader Semantic
Engine described in architecture and RFC documents must be reported according
to implemented evidence, not treated as complete because contracts exist.

### 6. Operator prototype

The **Operator prototype** is the browser interface in
[`site/operator/index.html`](../../site/operator/index.html). It may compose or
normalize a case, store a local draft, prepare a controlled handoff, and render
draft or returned output according to its implemented code.

The Operator is an interface. It is not:

- the Normative Kernel;
- the canonical v1 method;
- the scenario simulator;
- the complete Semantic Engine;
- an evidence verifier; or
- a governance approver or ratifier.

### 7. RFC and planned capability

An **RFC** is a versioned proposal for review. A Draft RFC is not a current
capability, accepted architecture, roadmap commitment, or normative rule.

An RFC becomes accepted only through an explicit human ratification record. An
accepted RFC authorizes only what its text states; implementation still requires
its own scoped issue, reviewable change, tests, and evidence. Code or prose that
exists without those records must not be promoted as implemented merely because
an RFC describes it.

## Semantic invariants and byte representation

### Semantic invariant

A **semantic invariant** is a proposition whose normative force must remain
stable within one Normative Kernel version. Examples include a prohibition, an
authority boundary, a required review property, or the meaning and order of a
Kernel principle.

The invariant is the meaning, not a particular punctuation mark, line wrapping,
translation, filename, or byte sequence.

### Byte representation

A **byte representation** is a particular encoded file at a particular commit.
Bytes can change through Git. Branch protection, CODEOWNERS, hashes, reviews,
and Kernel Guard may detect or restrict changes, but no such technical control
alone makes a change normatively legitimate.

Likewise, an unreviewed byte change does not become a valid constitutional
amendment merely because it was committed or merged.

### Candidate operational definition of `immutable`

Within a ratified Normative Kernel version, **immutable** would mean:

> No semantic invariant may be removed, weakened, reversed, silently
> reinterpreted, or given a new exception while that version identifier is
> retained.

Meaning-preserving byte changes may be proposed as maintenance. A semantic
change requires a new normative version and the full human amendment process.
No document should claim that repository bytes are technically impossible to
change.

### Candidate change classes

| Class | Meaning | Minimum window | Version effect |
| --- | --- | --- | --- |
| **K-PATCH: meaning-preserving maintenance** | Typo, formatting, link, encoding, or translation-parity correction with no change in normative force. | 7 calendar days | Increment `PATCH`. |
| **K-MINOR: compatible semantic amendment** | Adds a rule or clarification that does not remove, weaken, reverse, or except an existing invariant. | 21 calendar days | Increment `MINOR`; set `PATCH` to zero. |
| **K-MAJOR: protected or breaking amendment** | Removes, weakens, reverses, reorders, or creates an exception to an invariant; changes anti-capture, amendment mechanics, reviewer eligibility, ratifier authority, or the ownership/legitimacy boundary. | 30 calendar days | Increment `MAJOR`; set `MINOR` and `PATCH` to zero. |

A formal objection that a proposed K-PATCH changes meaning automatically pauses
the maintenance classification. The proposal must be revised to remove the
semantic effect or re-opened under K-MINOR/K-MAJOR. When classification cannot
be resolved from the record, the higher class applies.

## Candidate reconciliation: ownership, stewardship, and legitimacy

This section proposes an internal governance distinction, not a legal opinion.
External legal rights and obligations require the applicable records and, where
needed, qualified counsel.

### Legal and project control

Legal/project control concerns matters such as copyright, trademark, repository
administration, contracts, licensing decisions, and final human accountability.
The current versioned stewardship record identifies Benjamin Gerrit Hoff as
creator, project owner, Primary Human Steward, and final human-accountability
layer, with `@Voxterrae` as the repository identity. It identifies Rodrigo /
`@itteamrod` as Core Technical Steward within recorded boundaries.

This RFC does not confirm the external legal effect of those statements, expand
them, or transfer any right.

### Normative legitimacy

Normative legitimacy answers a different question:

> Was a semantic rule adopted through the transparent, anti-capture,
> human-accountable process required to present it as HUB_Optimus?

Under the candidate model:

- ownership or repository administration would not by itself ratify a semantic
  amendment;
- normative review would not transfer ownership, create a license, or confer
  repository administration;
- the Primary Human Steward would retain final human accountability while
  acting as a constrained ratifier, not a unilateral constitutional author;
- the Core Technical Steward could review affected technical coherence without
  acquiring project ownership or unilateral constitutional authority; and
- Custodianship would be a separately appointed normative role, not ownership.

The Kernel's anti-capture statement would therefore apply to **bypassing
normative process**. It would not erase separately documented legal rights,
administrative duties, or human accountability. Conversely, those separate
roles would not create a privilege to bypass normative review.

## Candidate amendment mechanics

These mechanics are deliberately complete enough that a later reviewer could
determine the outcome from GitHub records alone. They are not active while this
RFC remains Draft.

### 1. Required proposal packet

Every proposal must begin with one public GitHub issue containing:

1. the exact invariant or governance rule affected;
2. the proposed wording and change class;
3. rationale and expected impact;
4. compatibility analysis against each affected Kernel principle;
5. affected canonical files, language mirrors, contracts, and implementations;
6. claims, supporting and conflicting evidence, inferences, and uncertainties;
7. security, legal, IP, operational, and translation risks, marked as such;
8. migration and rollback plans;
9. AI or automated assistance used; and
10. the proposed eligible-reviewer roster and conflicts of interest.

The review PR must link the issue and identify the exact commit under review.
Material amendments after review opens require a new commit and restart the
applicable window.

### 2. Eligible human reviewers

The candidate eligible roster is the complete, deduplicated set of natural
persons who, when the review opens, are visibly recorded in at least one of
these categories:

1. a human project-stewardship role in
   [`PROJECT_STEWARDSHIP.md`](../governance/PROJECT_STEWARDSHIP.md);
2. a human Custodian appointed by a prior, ratified, versioned record; or
3. a human CODEOWNER for an affected normative path, provided the account maps
   to a named human in a versioned governance record.

One natural person counts once, regardless of accounts or roles. Organizations,
bots, model accounts, AI agents, and undisclosed delegates are not eligible.
Advisory domain experts and any member of the public may comment, but they do
not count toward quorum unless they already meet an eligibility category.

The full roster must be frozen in the issue before the review window opens. A
reviewer must disclose authorship, employment, financial, personal, or other
material conflicts. A recusal is recorded and excludes that person from the
voting denominator. If a recusal or roster change occurs after opening and
changes the denominator, the review window restarts. Fewer than two distinct,
non-recused eligible humans means ratification is unavailable and the last
ratified version remains in force.

This RFC appoints nobody. On the current records, the first human ratification
review would need to state explicitly which already recorded natural persons
meet these candidate categories.

### 3. Quorum and approval threshold

Let `N` be the frozen number of non-recused eligible human reviewers.

- **Participation quorum:** `Q = max(2, ceil(2N / 3))`.
- **Approval threshold for K-PATCH and K-MINOR:**
  `A = max(2, ceil(3N / 4))`.
- **Approval threshold for K-MAJOR:** all `N` eligible human reviewers.
- At least one approval must come from a human other than the proposer.
- Silence, an emoji, an automated check, an AI review, and absence of an
  objection are not approvals.
- A sustained formal objection blocks every class even if the numeric approval
  threshold has otherwise been met.

A participating reviewer must record one of: `approve`, `object`, or `abstain`,
with a short rationale. Abstention counts as participation but not approval.
The quorum, threshold, no-sustained-objection rule, and ratifier attestation must
all be satisfied. None substitutes for another.

### 4. Review window

The window begins only when the proposal packet, frozen roster, exact review
commit, rendered diff, and conflict disclosures are present.

- K-PATCH: 7 full calendar days.
- K-MINOR: 21 full calendar days.
- K-MAJOR: 30 full calendar days.

The issue must record opening and closing timestamps in UTC. Closing early is
not allowed. Material wording, scope, roster, evidence, or classification
changes restart the full applicable window. Review may remain open longer when
an objection or missing evidence is unresolved.

### 5. Formal objections and conflict handling

A blocking objection must:

- be made by an eligible, non-recused human reviewer;
- use the label `FORMAL OBJECTION`;
- cite the affected invariant, trust/verifiability rule, anti-capture boundary,
  authority rule, or material evidence gap;
- explain the predicted harm or contradiction; and
- state what evidence or revision could resolve it, where possible.

Every formal objection receives one visible status:

- `open`;
- `resolved by revision`;
- `withdrawn by objector`;
- `sustained`; or
- `out of scope`, with a separate follow-up issue and written rationale.

An objection is resolved when the objector accepts the response, or when at
least two eligible, non-conflicted reviewers who are neither proposer nor
objector document why the revised proposal answers it without Kernel conflict.
If that independent review is unavailable, the objection remains sustained.
The proposer or ratifier may not classify an objection as `out of scope`
unilaterally; that classification requires the same independent review.

Comments from non-eligible participants are advisory, but material evidence
they provide must receive a written disposition before ratification.

There is no substantive constitutional tie-breaker. A tie, an unresolved
classification dispute, an unresolved conflict of interest, or a sustained
objection means **not ratified**. The status quo prevails until a revised
proposal completes a new window. The ratifier may not override that result.

### 6. Human ratifier

The candidate ratifier is the natural person holding the versioned **Primary
Human Steward / final human-accountability** role in
[`PROJECT_STEWARDSHIP.md`](../governance/PROJECT_STEWARDSHIP.md). The current
document names Benjamin Gerrit Hoff; this RFC neither appoints nor removes him.

The ratifier may participate as an eligible reviewer but:

- may not be the only approving human;
- may not waive the window, quorum, threshold, evidence, or objection rules;
- may not convert repository administration into normative approval;
- may not ratify while a sustained objection remains; and
- must issue an explicit, human-authored ratification statement tied to the
  exact commit.

Merge access is not ratification. Ratification is not inferred from a merge,
release, label, bot action, silence, or chat statement.

### 7. Required ratification record

The final issue or PR record must make these fields decidable:

```text
Normative version:
Change class:
Proposal issue:
Review PR:
Reviewed commit:
Affected invariants/files:
Eligible roster (natural persons):
Recusals/conflicts:
Window opened (UTC):
Window closed (UTC):
Participation quorum Q / actual:
Approval threshold A / actual:
Formal objections and final status:
Advisory objections and disposition:
Translation/mirror status:
Checks and evidence:
AI/automation involvement:
Rollback target:
Human ratifier:
Ratification statement and timestamp:
Merge commit:
```

The exact ratification statement should be:

```text
I, <human name and versioned role>, RATIFY <normative version> at
<reviewed commit>. I confirm that the recorded human review window, roster,
quorum, approval threshold, objection resolution, translation status, and
evidence requirements were satisfied. No AI approval or self-ratification was
counted.
```

If a field is missing or contradicted by the record, ratification has not been
demonstrated.

### 8. Translation and effectiveness

The canonical amendment and its required mirrors must preserve the same
normative meaning. The ratification record must identify:

- the canonical text;
- each active translated mirror;
- any language classified by
  [`docs/context/STATUS.md`](../context/STATUS.md) as a stub rather than a
  ratified translation; and
- the review evidence used to check normative-strength parity.

A stub may point to the canonical source but must not be represented as a
completed, ratified translation. A new normative version does not become
effective until the mirror obligations in the then-current Translation Policy
are satisfied or an explicit ratified policy says otherwise.

### 9. Versioning

The candidate identifier is `NK-MAJOR.MINOR.PATCH`.

- `MAJOR` records a protected or breaking semantic amendment.
- `MINOR` records a compatible semantic amendment.
- `PATCH` records meaning-preserving maintenance.

Version identifiers are never reused. Each version must point to one ratified
commit and evidence record. Repository releases, tags, or hashes may strengthen
integrity evidence but do not replace human ratification.

Existing governance has no `NK-*` version record. This Draft does not assign one
retroactively. Initial version selection requires an explicit human
ratification decision.

### 10. Emergency containment

Emergency procedure is for containment, not accelerated constitutional
amendment. It may:

- restore the bytes of the last ratified Normative Kernel version;
- suspend publication or deployment of a disputed change;
- disable an affected implementation without redefining the invariant; or
- preserve evidence and repository integrity.

It may not introduce new normative meaning, expand authority, erase history,
or call an unreviewed change ratified.

An emergency action must record the triggering evidence, affected artifacts,
actor, timestamp, scope, and rollback target as soon as safely possible. The
Primary Human Steward may take a necessary administrative containment action
under separately documented project responsibilities, but that action remains
non-normative. It must receive one additional eligible human concurrence within
72 hours and open normal review within 7 calendar days, or be reversed where
reversal is technically and externally permissible.

Nothing in this candidate procedure claims to override applicable law,
contractual duties, platform action, or confidentiality obligations. Such
constraints must be recorded to the extent lawfully possible and reviewed
separately.

### 11. Rollback and invalid-process handling

Rollback preserves history. It never deletes or rewrites the deliberative
record.

- **Implementation rollback:** code, deployment, or interface behavior may be
  restored through its own scoped operational process without changing
  normative meaning.
- **Normative rollback:** restoring prior semantics is a new, traceable
  amendment and receives a new version; version numbers never move backward.
- **Emergency restoration:** the exact last ratified bytes may be restored
  temporarily under the emergency-containment rule.
- **Invalid process:** if the evidence record later shows no human ratification,
  insufficient quorum, counted AI approval, hidden conflict, or a sustained
  objection, the disputed version is marked `ratification not demonstrated`.
  The last demonstrated human-ratified version remains the normative reference
  while a corrective proposal is reviewed.

The corrective record must identify what failed, who determined it from the
record, which version remains effective, and what prevents recurrence.

## AI and automation boundary

AI systems and automation may:

- locate relevant files and GitHub records;
- draft candidate text;
- compare terminology and translations;
- summarize evidence and objections;
- run tests, link checks, encoding checks, and deterministic policy checks; and
- prepare a review packet.

They may not:

- enter the eligible-reviewer roster;
- count toward quorum or approval threshold;
- create a blocking formal objection in their own right;
- classify or dismiss objections with authority;
- serve as Custodian or ratifier;
- infer human approval from chat, silence, or tool execution;
- approve their own authored governance proposal;
- ratify or merge their own governance change; or
- use model capability, hidden prompts, memory, or automation as authority.

All AI findings remain advisory until a named human reviews and records the
decision in GitHub. Human ratification is mandatory.

## Adoption path for this RFC

This Draft cannot bootstrap its own authority. The candidate mechanics may be
used as a non-binding review checklist, but their authority cannot come from
applying them circularly to this same Draft.

Adoption would require:

1. human review under the governance rules that are current at that time;
2. an explicit human ratification record for this proposal;
3. a later focused issue and PR updating the canonical governance documents;
4. a separately reviewed Kernel manifest and initial `NK-*` version decision;
5. synchronized language handling under the current Translation Policy; and
6. no sustained human governance objection.

Until those steps occur, existing versioned governance remains unchanged and
this file remains `Draft`.

## Acceptance checks for human reviewers

Human reviewers should be able to answer:

- Does each use of `kernel` now refer to one unambiguous candidate term?
- Is canonical v1 methodology distinct from constitutional meaning and runtime?
- Does `immutable` protect semantics without making a false claim about bytes?
- Are legal/project control and normative legitimacy separate without
  transferring rights or inventing legal conclusions?
- Can eligibility, quorum, threshold, window, objections, and ratification be
  calculated from versioned records?
- Does deadlock preserve the last ratified state instead of granting hidden
  authority?
- Can an emergency contain harm without creating new constitutional meaning?
- Are rollback and version history preserved?
- Is human ratification explicit?
- Is AI self-approval impossible under the proposed rules?

## Validation for this Draft

The documentation-only PR should verify:

```bash
python tools/check_mojibake.py docs/rfc/constitutional_vocabulary_and_amendment_mechanics.md
git diff --check
python -m pytest -q
```

Repository link checks should also pass where the environment supports them.
