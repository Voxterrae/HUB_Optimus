# HUB_Optimus Scenario Contracts

## Purpose

HUB_Optimus intentionally keeps two different scenario contracts:

1. the rich human workflow template used to structure analysis and review; and
2. the strict executable JSON input accepted by the prototype simulator.

They are related authoring surfaces, not equivalent representations. Converting
a human workflow into executable JSON is a manual, lossy modelling decision.
The repository has no automatic converter, and executable acceptance does not
verify the human narrative or any real-world claim.

## Source boundaries

- Human workflow reference:
  [`../../v1_core/workflow/04_scenario_template.md`](../../v1_core/workflow/04_scenario_template.md)
- Lightweight repository authoring template:
  [`../scenarios/scenario_template.md`](../scenarios/scenario_template.md)
- Executable structure:
  [`../../scenario.schema.json`](../../scenario.schema.json)
- Authoritative JSON loader and cross-record validation:
  [`../../run_scenario.py`](../../run_scenario.py)
- Runtime behavior:
  [`../architecture/runtime_contract.md`](../architecture/runtime_contract.md)
- Operator guide:
  [`../../SIMULATION_README.md`](../../SIMULATION_README.md)
- Project source-of-truth precedence:
  [`../context/SOURCE_OF_TRUTH.md`](../context/SOURCE_OF_TRUTH.md)
- Canonical-language and mirror policy:
  [`../context/STATUS.md`](../context/STATUS.md)

The schema defines document structure. The loader additionally rejects
non-standard JSON constants and duplicate actor names. The applicable schema,
loader/source, tests, and runtime contract are authoritative for executable
behavior. `STATUS.md` governs canonical-language questions. This governance
document maps those boundaries; it does not replace or extend the executable
sources.

## Executable JSON contract

The root object has exactly five required fields. Unknown root fields and
unknown fields inside `roles[]` are rejected.

| JSON field | Accepted shape | Current loader/runtime use | What it does not imply |
|---|---|---|---|
| `title` | Non-empty, non-whitespace string | Stored on the runtime `Scenario`. It does not currently affect actor actions or success. | A workflow ID, version, evidence record, or verified real-world title. |
| `description` | Non-empty, non-whitespace string | Stored on the runtime `Scenario`. Current built-in policies do not read it. | Structured context, a timeline, truth verification, or an evaluated narrative. |
| `roles` | Non-empty array; each item contains only non-empty `name` and `role` strings | The loader requires unique `name` values. `name` identifies the actor and its history entry. `role` is passed to the selected policy; the current `biased` policy treats exact `hardliner` and `mediator` values specially, while the default policy and other role strings use the uniform offer behavior. | Objectives, constraints, authority, verification duties, biography, or a per-actor policy declaration. |
| `success_criteria` | Non-empty object whose values are JSON strings, numbers, integers, booleans, or `null` | After each round, success occurs when any actor action matches any one criterion key/value. Criteria therefore have OR, not AND, semantics. Current built-in policies emit only `offer`. The kernel compares `actor_action.get(key)` with the expected value, so a `null` criterion also matches an action that omits that key. | The human definition of minimum or extended success, verification, durability, stability, or policy quality. |
| `max_rounds` | Integer greater than or equal to `1` | Sets the maximum number of rounds. Failure is returned if no mechanical criterion matches before the cap. | A round agenda, sequence, deadline, negotiation plan, or guarantee that all planned rounds occur. |

Executable files must be standard JSON. YAML and the non-standard constants
`NaN`, `Infinity`, and `-Infinity` are not accepted. Schema and identity
validation establish input integrity only; they do not establish factual
accuracy.

## Field-by-field relationship to the rich human workflow

| Human workflow section | Possible manual projection into JSON | Narrative-only or otherwise absent from the runtime |
|---|---|---|
| **0. Metadata** — ID, version, language, updated date, author, status | A human may choose a short display value for `title`. There is no automatic derivation. | Version, language, dates, authorship, workflow status, and change history have no executable field. |
| **1. Executive summary** — situation, minimum objective, source of difficulty | A short contextual summary may be written manually as `description`. | The runtime stores but does not evaluate the summary, objective, difficulty, or factual basis. |
| **2. Actors and roles** — parties, third parties, objectives, limits, pressure | Actor identifiers and short role labels may be projected into `roles[].name` and `roles[].role`. Names must be unique. | Objectives, limits, internal pressure, authority, and relationships have no executable representation. Extra keys inside a role are rejected. |
| **3. Context and timeline** — prior context, recent events, horizon | Selected context may be condensed manually into `description`. | Events, dates, temporal relationships, milestones, and time horizons are not modelled. |
| **4. Interests, positions, and constraints** — interests, demands, internal constraints, red lines, flexibility | No direct projection. | All fields in this section are narrative-only. They cannot be added to `roles[]` without a schema change. |
| **5. Minimum objective and success criteria** — minimum success, extended success, clear failure | Only a criterion expressible as an action key and scalar JSON value may be encoded manually in `success_criteria`. | Human outcome quality, extended success, clear failure, durability, and verification are not evaluated. Multiple JSON entries are alternatives; they are not a conjunction. |
| **6. Initial proposal** — action, schedule, geography, exceptions, verification, non-compliance measures | No direct projection. | The current JSON cannot preload a proposal, schedule, geography, exception, or enforcement measure. Built-in policies generate simple `offer` actions at runtime. |
| **7. Verification and compliance** — verifier, subject, method, frequency, access, disputes | No direct projection. | The simulator has no evidence, sensor, access-control, compliance, dispute-resolution, or Trust Layer integration. |
| **8. Risks and friction points** — misunderstandings, cheating incentives, ambiguity, spoilers, incidents | No direct projection. | Risks and causal or adversarial dynamics are not consumed by the current runtime. |
| **9. Recommended rounds** — phase guidance, agreement draft, open points, next steps | A human may choose `max_rounds` as a mechanical cap. | Phase content, sequencing, deliverables, open points, ownership, and deadlines are not executable. |
| **10. Post-mortem evaluation** — clarity, verifiability, viability, political cost, escalation risk | No input projection. | The result fields `status`, `rounds`, `history`, and `detail` are mechanical run data; they do not calculate these evaluation scores. |
| **11. Meta-learning** — lessons, failures, missing definitions, future changes, new questions | No direct projection. | The runtime does not update scenarios, learn from runs, or create governance conclusions. |

## Relationship to the lightweight authoring template

[`../scenarios/scenario_template.md`](../scenarios/scenario_template.md) is a
repository proposal and review aid, not a simulator input file. Its title,
short context, actor labels, and a mechanically expressible success condition
may inform `title`, `description`, `roles`, and `success_criteria` through
manual authoring. It has no dedicated `max_rounds` field; the executable cap
must be chosen separately. Scenario family, tension, failure mode, invariants,
benchmark plan, and notes have no direct runtime field. A benchmark proposal
does not become a frozen benchmark merely because an executable JSON file
exists.

## Runtime controls are not scenario fields

The supported CLI exposes controls outside the JSON document:

- the positional scenario path or `--scenario` selects the JSON input file;
- `--seed` selects a reproducible random stream;
- `--policy` selects one supported policy for all actors (`uniform` or
  `biased`); and
- `--output` selects the result path.

Human per-actor strategies, evidence, verification rules, and negotiation
phases cannot be encoded by adding these names to the JSON. Unknown fields are
rejected.

## Minimal projection example

A human workflow might describe several parties, interests, risks, safeguards,
and a verified agreement. The following executable projection preserves only
two actor labels, one mechanical offer condition, and a five-round cap:

```json
{
  "title": "Partial ceasefire",
  "description": "Two factions negotiate a partial ceasefire.",
  "roles": [
    {"name": "FactionA", "role": "negotiator"},
    {"name": "FactionB", "role": "negotiator"}
  ],
  "success_criteria": {"offer": 5},
  "max_rounds": 5
}
```

A successful run means only that at least one generated action contained
`"offer": 5` before the cap. It does not mean that a ceasefire was negotiated,
verified, durable, legitimate, or advisable.

## Change discipline

- Do not place human-only fields in executable JSON; validation will reject
  them.
- Do not describe the human template as executable or the JSON as a complete
  analytical scenario.
- Any executable-field change requires one scoped change that updates
  `scenario.schema.json`, the loader/runtime as applicable, examples, tests,
  and the runtime documentation together.
- Any richer human-to-runtime translation requires an explicitly approved
  schema/runtime issue. This mapping alone grants no such capability.

## Translation maturity

This English governance document is canonical for this surface. German,
Spanish, Catalan, French, and Russian mirrors remain `review-needed`. Hebrew
and Simplified Chinese remain `stub`. These states are declared in
[`../i18n/maturity.v1.json`](../i18n/maturity.v1.json); structural or automated
checks do not certify linguistic quality, professional review, or parity.
