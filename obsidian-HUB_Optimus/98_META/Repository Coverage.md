---
type: meta
status: partial
layer: project-intelligence
criticality: high
source:
  - site/obsidian-HUB_Optimus/system.json
  - site/obsidian-HUB_Optimus/system.runtime.json
  - site/obsidian-HUB_Optimus/system.learning.json
tags:
  - coverage
  - source-map
  - drift
baseline_commit: 30e985226347b4bc59b0e187b96633a09647ca42
v1_candidate_commit: 9c7b5d81b2cf85d349b1ca141d559a75067a9b14
---

# Repository Coverage

## Current confirmed semantic coverage

For baseline commit `30e985226347b4bc59b0e187b96633a09647ca42`, the reviewed model contains:

| Model object | Count |
|---|---:|
| Components | 16 |
| Interfaces | 7 |
| Entities | 13 |
| Relations | 25 |
| Risks | 8 |

These counts come from the synchronized v1 JSON model deployed from candidate `9c7b5d81b2cf85d349b1ca141d559a75067a9b14`.

## What this proves

The semantic model covers the components, interfaces, entities, runtime flows, deployment boundaries and risks explicitly represented by the reviewed Project Intelligence snapshot. [[Source Map]] connects those concepts to repository paths.

## What this does not prove

The current model does not claim complete machine-measured coverage of every repository file. A deterministic recursive inventory and an unmodelled-surface report are `planned` for v1.1.

It also does not prove mutable external state such as repository settings, Pages runtime, EC2, DNS, TLS or Nginx.

## v1.1 coverage dimensions

1. **Semantic coverage** — which system concepts are represented.
2. **Source coverage** — which repository paths support those concepts.
3. **Test coverage map** — which tests and workflows protect each concept.
4. **Change coverage** — which model facts are affected by a Git delta.
5. **External-state coverage** — which mutable objects were directly inspected.

Each dimension must be reported separately. A high value in one dimension cannot substitute for evidence in another.

## Planned quality gates

- every model source path resolves at the pinned commit;
- every relation identifies supported endpoints;
- every published view remains closed over its nodes and relations;
- unmapped repository domains are listed rather than ignored;
- stale evidence is flagged rather than silently reused;
- external state is never inferred from source presence.

## Related

- [[Whole-System Learning]]
- [[Evidence Index]]
- [[Testing Strategy]]
- [[Risk Register]]
- [[Update Protocol]]
