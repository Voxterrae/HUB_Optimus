---
type: "component"
status: "partial"
layer: "frontend"
criticality: "high"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "site/operator/index.html"
  - "site/operator/sw.js"
  - "site/operator/learning-candidate.v1.js"
  - "site/operator/learning-store.v1.js"
tags:
  - "frontend"
  - "operator"
  - "pwa"
---

# Operator PWA

> **Estado:** `partial` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Preparar en el navegador intake estructurado, borradores con procedencia y una revisión humana local.

## Responsibilities

- Mantener una interfaz accesible y multilingüe.
- Separar borradores locales de evidencia verificada y resultados del engine.
- Conservar el trabajo local sin afirmar backend público.

## Runtime Behaviour

Se ejecuta en el navegador como HTML/CSS/JavaScript y PWA. El flujo público actual permanece local/manual y no prueba disponibilidad de un backend.

## Inputs

- texto pegado
- URL como referencia
- metadatos y revisión humana

## Outputs

- borradores locales
- CaseInput compatible
- learning candidates no canónicos

## Dependencies

- Browser APIs
- Service Worker
- local storage/IndexedDB modules

## Consumers

- Operadores humanos

## Data

- source-bound draft
- review state
- learning candidate

## APIs

- Browser UI
- PWA
- export/copy handoff

## Failure Modes

- pérdida de almacenamiento local
- confundir draft con evidencia
- interpretar una URL sin texto como fetch realizado

## Security

Local-first; la procedencia y la revisión humana son obligatorias. No hay autenticación pública implementada.

## Tests

- `tests/test_operator_pwa_product_actions.py`
- `tests/test_operator_pwa_record_integrity.py`
- `tests/test_operator_learning_ui.py`

## Deployment

Archivos estáticos bajo site/operator/ publicados por Pages cuando el workflow se ejecuta.

## Source Files

- `site/operator/index.html`
- `site/operator/sw.js`
- `site/operator/learning-candidate.v1.js`
- `site/operator/learning-store.v1.js`

## Related Components

- [[Operator Learning Store]]
- [[Public Static Site]]
- [[Semantic Engine Contracts and CLI]]
- [[Operator Learning Data]]
- [[Semantic Data Model]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
