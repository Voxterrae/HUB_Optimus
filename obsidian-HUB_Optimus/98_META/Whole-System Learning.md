---
type: meta
status: experimental
layer: project-intelligence
criticality: high
source:
  - site/obsidian-HUB_Optimus/system.learning.json
  - site/obsidian-HUB_Optimus/app-v11.js
tags:
  - evidence
  - learning
  - provenance
  - maintenance
baseline_commit: 30e985226347b4bc59b0e187b96633a09647ca42
v1_candidate_commit: 9c7b5d81b2cf85d349b1ca141d559a75067a9b14
---

# Whole-System Learning

## Definition

“Learning” in HUB_Optimus Project Intelligence means a repeatable process that converts repository observations into reviewed, source-bound model facts. It does not mean autonomous truth adjudication, prediction or opaque training over repository content.

The semantic baseline remains commit `30e985226347b4bc59b0e187b96633a09647ca42`; the exact reviewed v1 candidate is `9c7b5d81b2cf85d349b1ca141d559a75067a9b14`.

## Required dimensions

Every learned claim must retain:

1. the claim itself;
2. repository source or direct external observation;
3. analyzed commit and tree;
4. implementation status;
5. epistemic confidence;
6. freshness;
7. review state.

The permitted status and confidence vocabulary remains defined by [[Status Definitions]].

## Learning pipeline

```text
Repository commit + tree
        ↓
Changed-path inventory
        ↓
Affected-domain classification
        ↓
Evidence re-evaluation
        ↓
Model delta
        ↓
Obsidian + JSON + graph synchronization
        ↓
Structural and production validation
```

## v1.1 workstreams

### Active or experimental

- graph node search;
- direct, upstream and downstream impact focus;
- zoom, pan and fit controls;
- relation-evidence inspection;
- visible learning contract and model coverage summary.

### Planned

- deterministic recursive repository inventory;
- unmodelled-surface report;
- source → component → interface → entity → test → deployment coverage;
- documentation-drift delta;
- change-impact report tied to Git commits;
- incremental regeneration of affected notes and views.

Planned capabilities remain labelled `planned`; they are not presented as implemented.

## Boundaries

- Code presence does not prove live deployment.
- A document does not override executable source, active configuration, schemas or tests in their own domains.
- A draft, local learning candidate or intake record is not canonical evidence.
- An inference remains `INFERRED` until evidence changes.
- Mutable repository settings, DNS, TLS, EC2 and service state remain `UNKNOWN` until directly inspected.

## Maintenance

Use [[Update Protocol]] for the existing v1 update procedure. v1.1 adds delta analysis: identify changed evidence first, then update only affected facts while preserving historical discrepancy.

## Related

- [[Repository Coverage]]
- [[Graph Intelligence v1.1]]
- [[Documentation Standard]]
- [[Evidence Index]]
- [[Current State]]
