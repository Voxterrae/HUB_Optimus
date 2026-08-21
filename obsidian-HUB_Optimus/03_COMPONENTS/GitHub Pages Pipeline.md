---
type: "component"
status: "active"
layer: "deployment"
criticality: "medium"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - ".github/workflows/pages.yml"
tags:
  - "deployment"
  - "github-actions"
  - "pages"
---

# GitHub Pages Pipeline

> **Estado:** `active` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Publicar exactamente el árbol site/ en GitHub Pages tras cambios aprobados en main.

## Responsibilities

- Checkout del commit de main.
- Configurar Pages y subir site/ como artefacto.
- Desplegar mediante la acción oficial fijada por SHA.

## Runtime Behaviour

pages.yml se dispara por push a main para site/docs/brand/workflow o manualmente; no ejecuta build de frontend.

## Inputs

- commit aprobado en main
- site/

## Outputs

- Pages artifact
- deployment record

## Dependencies

- GitHub Actions
- GitHub Pages

## Consumers

- Public Static Site
- Operator PWA
- Project Intelligence Explorer

## Data

- static site artifact
- deployment status

## APIs

- GitHub Actions workflow

## Failure Modes

- workflow failure
- artifact missing
- deployment environment failure
- Pages settings mismatch

## Security

Permisos mínimos contents:read, pages:write e id-token:write; el estado vivo requiere inspección externa.

## Tests

- `tests/test_workflow_action_pins.py`
- `tests/test_public_portfolio.py`

## Deployment

Es el mecanismo de despliegue de Pages; la fuente está confirmada, una ejecución concreta debe verificarse en GitHub.

## Source Files

- `.github/workflows/pages.yml`

## Related Components

- [[Architecture Overview]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
