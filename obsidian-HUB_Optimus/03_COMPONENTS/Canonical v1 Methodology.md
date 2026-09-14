---
type: "component"
status: "active"
layer: "methodology"
criticality: "high"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "docs/context/STATUS.md"
  - "v1_core/languages/es/01_base_declaracion.md"
  - "v1_core/languages/es/02_arquitectura_base.md"
  - "v1_core/languages/es/03_flujo_operativo.md"
  - "v1_core/workflow/README.md"
tags:
  - "methodology"
  - "canonical"
  - "human-review"
---

# Canonical v1 Methodology

> **Estado:** `active` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Proporcionar el marco humano de evaluación estructurada, incentivos, verificación, secuencia y estabilidad.

## Responsibilities

- Definir el método v1 en español como fuente canónica.
- Mantener el inglés como objetivo de paridad y las demás traducciones con madurez declarada.
- Guiar el uso humano sin fingir que el runtime ejecuta toda la metodología.

## Runtime Behaviour

Los documentos metodológicos son leídos y aplicados por personas; el código ejecutable no los carga como política autónoma.

## Inputs

- escenarios
- afirmaciones
- evidencia
- incertidumbre
- contexto humano

## Outputs

- evaluación estructurada humana
- opciones preventivas
- aprendizaje documentado

## Dependencies

- STATUS.md
- translation maturity records
- human review

## Consumers

- Operadores
- revisores
- autores de escenarios

## Data

- Markdown canónico y traducciones

## APIs

- Obsidian
- documentación
- scenario workflow

## Failure Modes

- deriva entre idiomas
- confundir método con implementación
- convertir narrativa en evidencia

## Security

No otorga autoridad ni ejecuta acciones; mantiene límites de no coerción y revisión humana.

## Tests

- `tests/test_core_es_en_parity_matrix.py`
- `tests/test_i18n_maturity.py`

## Deployment

Se publica como documentación versionada; no existe un servicio metodológico autónomo.

## Source Files

- `docs/context/STATUS.md`
- `v1_core/languages/es/01_base_declaracion.md`
- `v1_core/languages/es/02_arquitectura_base.md`
- `v1_core/languages/es/03_flujo_operativo.md`
- `v1_core/workflow/README.md`

## Related Components

- [[Round-based Simulator]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
