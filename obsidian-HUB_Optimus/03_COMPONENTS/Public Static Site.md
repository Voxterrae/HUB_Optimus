---
type: "component"
status: "active"
layer: "frontend"
criticality: "medium"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "site/index.html"
  - "site/styles.css"
  - "site/app.js"
  - "site/globe.js"
tags:
  - "frontend"
  - "static-site"
  - "pages"
---

# Public Static Site

> **Estado:** `active` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Presentar la identidad pública, límites del proyecto, documentación y acceso al Operator mediante una experiencia estática.

## Responsibilities

- Servir HTML/CSS/JavaScript sin backend obligatorio.
- Mantener accesibilidad, responsive y reduced motion.
- Separar claims públicos de evidencia versionada.

## Runtime Behaviour

El navegador carga archivos de site/ directamente desde Pages; app.js y globe.js mejoran progresivamente la experiencia.

## Inputs

- assets estáticos
- locale metadata
- browser capabilities

## Outputs

- portfolio público
- visualización WebGL con fallback
- rutas documentales

## Dependencies

- browser
- GitHub Pages
- static assets

## Consumers

- visitantes públicos

## Data

- i18n dictionaries
- GeoJSON
- pinned evidence routes

## APIs

- Web UI
- /
- /operator/
- /obsidian-HUB_Optimus/

## Failure Modes

- asset 404
- WebGL no disponible
- enlace de evidencia obsoleto
- claim público fuera de alcance

## Security

Sin secretos ni backend embebido; enlaces públicos deben permanecer fijados a evidencia.

## Tests

- `tests/test_public_portfolio.py`
- `tests/test_operator_primary_i18n.py`

## Deployment

El workflow Pages sube el directorio site/ como artefacto estático.

## Source Files

- `site/index.html`
- `site/styles.css`
- `site/app.js`
- `site/globe.js`

## Related Components

- [[Operator PWA]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
