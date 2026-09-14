---
type: "meta-standard"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "meta"
  - "status"
  - "epistemic"
---

# Status Definitions

## Component Status

| Status | Meaning |
| --- | --- |
| `active` | Implemented or governing within a clearly bounded current contract. |
| `partial` | Bounded implementation exists, but integration, breadth or external state is incomplete/unverified. |
| `experimental` | Research/tooling/prototype not suitable as a general product claim. |
| `deprecated` | Retained but superseded; requires direct evidence. |
| `planned` | Explicit approved plan with no implementation; proposals alone do not qualify. |
| `unknown` | Evidence is insufficient, external or mutable. |

## Evidence Confidence

| Confidence | Meaning |
| --- | --- |
| `CONFIRMED` | Directly supported by current source/config/schema/test/workflow or inspected record. |
| `INFERRED` | Reasoned interpretation with supporting evidence and explicit uncertainty. |
| `UNKNOWN` | Cannot be established from the available baseline. |

## Important Distinctions

- `active source` ≠ `active deployment`.
- `partial` ≠ defective; it states an intentional or unresolved boundary.
- `experimental` outputs ≠ real-world evidence.
- `planned` document ≠ authorized implementation.
- `CONFIRMED` code ≠ certified legal/security/scientific outcome.

## Related

- [[Documentation Standard]]
- [[Capabilities]]
- [[Risk Register]]
