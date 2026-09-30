---
type: architecture
status: experimental
layer: frontend
criticality: medium
source:
  - site/obsidian-HUB_Optimus/app-v11.js
  - site/obsidian-HUB_Optimus/styles-v11.css
  - site/obsidian-HUB_Optimus/system.learning.json
tags:
  - architecture
  - visualization
  - project-intelligence
baseline_commit: 30e985226347b4bc59b0e187b96633a09647ca42
v1_candidate_commit: 9c7b5d81b2cf85d349b1ca141d559a75067a9b14
---

# Graph Intelligence v1.1

## Purpose

v1.1 evolves the static-layout architecture explorer into an interrogable graph without changing the underlying system facts. The graph remains a view over the same evidence-bound model described by [[Architecture Overview]], [[Source Map]] and [[Evidence Index]].

## Confirmed baseline

The reviewed v1 model is fixed to repository commit `30e985226347b4bc59b0e187b96633a09647ca42` and the deployed v1 candidate is `9c7b5d81b2cf85d349b1ca141d559a75067a9b14`.

The first v1.1 increment is additive. It does not change the HUB_Optimus runtime, `/operator/`, API contracts, schemas, Pages pipeline, permissions or repository rules.

## Interaction model

### Node search

Search spans only model nodes already present in `system.json` and `system.runtime.json`:

- component name and identifier;
- purpose;
- layer, category or external kind;
- repository source paths.

Selecting a match switches to a published view that already contains that node.

### Impact focus

The focus selector derives context from existing typed relations:

- `all`: preserve the full published view;
- `direct`: selected node plus immediate neighbours;
- `upstream`: nodes that can reach the selected node through directed relations;
- `downstream`: nodes reachable from the selected node.

No inferred edge is created by the browser.

### Viewport controls

Zoom, pan and fit alter only the SVG `viewBox`. They do not modify layouts, model data or source evidence.

### Relation evidence

The inspector displays relation labels, types, status and confidence from the structured model. Unrelated nodes remain visible but de-emphasized so the operator does not lose context.

## Accessibility

- keyboard-operable search, scope and zoom controls;
- keyboard shortcuts on the graph: `+`, `-`, `0`;
- focus state preserved by the v1 renderer;
- mobile layout collapses controls and keeps simplified node navigation;
- `prefers-reduced-motion` removes added transitions.

## Failure boundary

If the v1.1 learning fragment cannot load, the v1 graph remains available. If the v1 core model cannot load, the existing static fallback remains the authority.

## Related

- [[Architecture Overview]]
- [[Dependency Graph]]
- [[Runtime Architecture]]
- [[Testing Strategy]]
- [[Whole-System Learning]]
