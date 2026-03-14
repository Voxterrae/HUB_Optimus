# Scenario Taxonomy v0

This document defines the first taxonomy for diplomatic scenarios in
HUB_Optimus. Its purpose is to keep the scenario corpus structured as new
contributions arrive.

This taxonomy is conceptual only. It does not change runtime behavior, JSON
schema, benchmark rules, or simulator features.

---

## Scope

- Assign each scenario to one primary family.
- Choose the family based on the main diplomatic bottleneck, not on file
  format or writing style.
- Use secondary notes only as modifiers. They do not create a second family.

Example: a ceasefire that uses a mediator is still a `Ceasefire Negotiation`
scenario if the core question is whether violence can be paused credibly.

---

## Family definitions

| Family | Primary question | Typical actors involved | Common failure mode | Example scenario idea |
|---|---|---|---|---|
| Ceasefire Negotiation | Can parties pause or reduce violence under terms that can hold? | Armed factions, government forces, monitors, humanitarian coordinators | Symbolic agreement without credible verification or sequencing | Local ceasefire around a civilian corridor |
| Mediated Negotiation | Can a third party make an agreement possible by sequencing, guarantees, or shuttle diplomacy? | Two disputing parties, mediator, guarantor state, observer mission | Mediator lacks leverage, neutrality, or enforcement capacity | External mediator brokers phased de-escalation steps |
| Coalition Stability | Can one side keep its own coalition together long enough to negotiate externally? | Coalition partners, cabinet factions, military leadership, parliamentary blocs | Internal veto player defects after provisional concessions | Wartime unity government splits over negotiation terms |
| Shared Resource Conflict | Can rivals agree on access, allocation, or governance of a scarce shared asset? | Neighboring states, local authorities, technical agencies, affected communities | Zero-sum framing blocks technical compromise | Cross-border river basin drought-sharing arrangement |
| Spoiler Dynamics | Can negotiations survive actors who benefit from breakdown or escalation? | Formal negotiators, splinter militias, extremist factions, security services | Attack or provocation destroys trust before verification can stabilize it | Splinter group sabotages talks after a draft agreement |
| Domestic Political Pressure | Can negotiators sustain an agreement under elections, protest cycles, or media pressure? | Executive branch, opposition, public opinion blocs, media, civil society | Leaders optimize for optics at home and abandon workable terms | Election-season prisoner exchange under nationalist pressure |
| Asymmetric Negotiation | Can actors with sharply unequal power, legitimacy, or time horizons reach a durable bargain? | State and non-state actors, patron states, aid agencies, local power brokers | Dominant party imposes terms that look efficient but cannot be reciprocally enforced | Armed group seeks aid access under blockade conditions |

---

## Classification rule

When a scenario could appear to fit more than one family, classify it by the
single pressure that most strongly determines success or failure.

Use this order of reasoning:

1. What is the core agreement being attempted?
2. What is the main reason that agreement could fail?
3. Which family best captures that failure pressure?

If the answer still looks ambiguous, prefer the family that is most useful for
coverage accounting.

---

## Current repository coverage

The current benchmark pack is concentrated in one family:

- `Ceasefire Negotiation`

That is acceptable for v0, but it means future benchmark contributions should
expand coverage into the other families rather than only adding more ceasefire
variants.

The narrative workflow corpus now reaches a second family:

- `Coalition Stability`

This is useful exploratory coverage, but it is not yet benchmarked.

### Classification of current benchmark scenarios

| Scenario | Location | Primary family | Reason |
|---|---|---|---|
| `ceasefire_basic` | `benchmarks/scenarios/ceasefire_basic.json` | Ceasefire Negotiation | Bilateral ceasefire with compatible objectives and low convergence friction |
| `ceasefire_fragile` | `benchmarks/scenarios/ceasefire_fragile.json` | Ceasefire Negotiation | The mediator is important, but the main evaluation target is still whether a fragile ceasefire can converge under tight rounds |
| `ceasefire_failure` | `benchmarks/scenarios/ceasefire_failure.json` | Ceasefire Negotiation | Hardline bilateral ceasefire failure case with no feasible settlement space |

### Classification of current workflow scenario references

| Scenario | Location | Primary family | Reason |
|---|---|---|---|
| `scenario_001_partial_ceasefire` | `v1_core/workflow/scenario_001_partial_ceasefire.md` | Ceasefire Negotiation | Evaluates an unverifiable ceasefire as a destabilizing structure |
| `scenario_002_verified_ceasefire` | `v1_core/workflow/scenario_002_verified_ceasefire.md` | Ceasefire Negotiation | Evaluates a verified ceasefire as a stabilizing structure |
| `scenario_003_coalition_fracture` | `v1_core/workflow/scenario_003_coalition_fracture.md` | Coalition Stability | Evaluates how an internal veto player can collapse external diplomatic progress |

---

## Contribution guidance

When proposing a new scenario:

- start by selecting one primary family from this taxonomy,
- explain why that family is the best fit,
- avoid creating near-duplicates of existing scenarios unless the new scenario
  tests a clearly different failure mode,
- update the scenario catalog after the scenario is added.

Related documents:

- [scenario_template.md](scenario_template.md)
- [catalog.md](catalog.md)
