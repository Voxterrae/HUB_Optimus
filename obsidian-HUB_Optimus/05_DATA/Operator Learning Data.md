---
type: "data-model"
status: "partial"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "site/operator/schemas/operator_learning_candidate.v1.schema.json"
  - "site/operator/learning-store.v1.js"
tags:
  - "data"
  - "operator"
  - "indexeddb"
---

# Operator Learning Data

## Authority

`authority = local-non-canonical`

El modelo no entrena un sistema, no actualiza Core y no crea autoridad.

## Candidate Structure

- version and candidate identity;
- method reference pinned by path/hash;
- case reference and state (`draft`, `accepted`, `rejected`);
- timestamps;
- graph nodes and relations;
- three-to-five metrics;
- iteration decision and next experiment;
- closure checklist;
- append-only history.

## Required Graph Semantics

El schema exige, entre otros:

- exactamente un case node;
- claims y evidence;
- un outcome;
- varios signals;
- diagnosis, gap y action;
- relaciones tipadas entre esos nodos.

## Local Store

`learning-store.v1.js` usa IndexedDB:

- un object store versionado;
- límites de entradas y bytes;
- hashes SHA-256;
- validación del store completo;
- tokens de concurrencia;
- transiciones de estado puras;
- fail-closed ante unavailable, blocked, corrupt, quota o conflict.

## Acceptance Boundary

La aceptación local requiere closure completa y binding actual. Aun aceptado, el registro sigue sin convertirse en canonical Core o evidence verificada.

## Related

- [[Operator PWA]]
- [[Operator Learning Store]]
- [[Data Architecture]]
- [[Security Boundaries]]
