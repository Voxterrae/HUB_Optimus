# Scenario Authoring Template

Use this template when proposing a new diplomatic scenario for the repository.
It is intentionally lightweight: the goal is to define a scenario clearly
enough that maintainers can classify it, compare it, and decide whether it
belongs in the benchmark corpus.

This template complements the detailed workflow material in
[`v1_core/workflow/04_scenario_template.md`](../../v1_core/workflow/04_scenario_template.md).
It does not replace the runtime schema in
[`scenario.schema.json`](../../scenario.schema.json).

---

## Author instructions

- Pick one primary family from [scenario_taxonomy.md](scenario_taxonomy.md).
- Keep the context short and concrete.
- Describe failure as a structural breakdown, not as a personal judgment.
- If you think the scenario should become a benchmark, write invariants that a
  simulator run could check later.
- Do not change runtime, schema, or CI as part of this document.

---

## Copy-paste template

```markdown
# Scenario title

## Scenario family
- Primary family:
- Why this family is the best fit:
- Optional secondary characteristics:

## Context
Short narrative description of the diplomatic situation.

## Actors
- Actor 1:
- Actor 2:
- Actor 3 (optional):

## Tension
What makes the negotiation difficult.

## Success criteria
- Minimum acceptable outcome:
- Strong outcome (optional):

## Failure mode
Typical way the negotiation could break down.

## Invariants
- Property 1:
- Property 2:
- Property 3 (optional):

## Benchmark plan
- yes
- experimental
- undecided

## Notes
Anything maintainers should know about scope, novelty, or relation to existing scenarios.
```

---

## Section guidance

### Scenario title

Use a short, descriptive name. Prefer stable names such as
`coalition_fracture_budget_vote` over broad labels such as `hard case`.

### Scenario family

Choose the family that best captures the dominant negotiation constraint.
If the scenario mixes several dynamics, explain which one is primary.

### Context

Keep this to a short paragraph. Include only facts needed to understand why the
scenario exists.

### Actors

List roles, not biographies. Good examples:

- governing coalition,
- regional armed faction,
- external mediator,
- water authority.

### Tension

Name the force that makes agreement hard: lack of trust, domestic vetoes,
verification gaps, time pressure, resource scarcity, spoilers, or power
asymmetry.

### Success criteria

Write outcomes that can later be reviewed or simulated. Avoid vague targets
such as "better relations."

### Failure mode

Describe the most likely structural breakdown:

- agreement collapses after first implementation step,
- coalition partner defects before ratification,
- spoiler attack resets trust,
- resource allocation formula becomes politically unacceptable.

### Invariants

These are expected properties of a valid run or review. Examples:

- agreement should occur before `max_rounds`,
- mediator must appear before final agreement,
- no success result should be recorded if verification is absent,
- failure should remain possible under adversarial seeds.

### Benchmark plan

Use one of these values:

- `yes`: intended for stable, maintained benchmark coverage,
- `experimental`: useful for exploration but not yet frozen,
- `undecided`: worth discussing before committing to benchmark maintenance.

---

## Review checklist

Before opening a PR, confirm that:

- the scenario has one clear primary family,
- the failure mode is distinct from existing catalog entries,
- the scenario can be described without schema changes,
- the benchmark plan is explicit.

Related documents:

- [scenario_taxonomy.md](scenario_taxonomy.md)
- [catalog.md](catalog.md)
