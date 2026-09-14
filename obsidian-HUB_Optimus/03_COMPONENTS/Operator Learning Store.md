---
type: "component"
status: "partial"
layer: "data"
criticality: "medium"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "site/operator/learning-store.v1.js"
  - "site/operator/learning-candidate.v1.js"
  - "site/operator/schemas/operator_learning_candidate.v1.schema.json"
tags:
  - "data"
  - "indexeddb"
  - "local-first"
---

# Operator Learning Store

> **Estado:** `partial` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Persistir candidatos de aprendizaje locales, versionados y revisados por humanos sin convertirlos en memoria canónica.

## Responsibilities

- Validar el modelo operator_learning_candidate.v1.
- Persistir un store local en IndexedDB con límites y hashes.
- Fallar cerrado ante corrupción, conflicto, cuota o dependencia no disponible.

## Runtime Behaviour

El adaptador JavaScript abre una base IndexedDB versionada, valida el store completo y aplica transiciones append-only y controles de concurrencia.

## Inputs

- learning candidate
- estado previo y tokens SHA-256

## Outputs

- store local validado
- export local
- errores clasificados

## Dependencies

- IndexedDB
- TextEncoder
- SHA-256 helper
- learning candidate model

## Consumers

- Operator PWA
- revisor humano local

## Data

- LearningCandidate
- history events
- closure checks
- entry hashes

## APIs

- JavaScript module API

## Failure Modes

- IndexedDB no disponible
- quota
- schema inesperado
- conflicto de versión
- corrupción

## Security

Datos locales, no canónicos y sin sincronización remota probada. La aceptación requiere cierre completo y binding vigente.

## Tests

- `tests/test_operator_learning_store.py`
- `tests/test_operator_learning_candidate.py`

## Deployment

Se entrega como asset estático del Operator; el contenido vive en el navegador del usuario.

## Source Files

- `site/operator/learning-store.v1.js`
- `site/operator/learning-candidate.v1.js`
- `site/operator/schemas/operator_learning_candidate.v1.schema.json`

## Related Components

- [[Operator PWA]]
- [[Operator Learning Data]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
