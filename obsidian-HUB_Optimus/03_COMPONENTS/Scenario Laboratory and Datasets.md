---
type: "component"
status: "experimental"
layer: "research"
criticality: "medium"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "tools/scenario_generator/"
  - "tools/scenario_mutator.py"
  - "tools/scenario_telemetry.py"
  - "benchmarks/"
tags:
  - "research"
  - "experimental"
  - "datasets"
---

# Scenario Laboratory and Datasets

> **Estado:** `experimental` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Generar, mutar, medir y comparar escenarios y datasets sintéticos de forma reproducible.

## Responsibilities

- Reutilizar el loader canónico de escenarios.
- Generar manifests y observaciones deterministas.
- Mantener outputs sintéticos separados de hechos reales.

## Runtime Behaviour

Herramientas CLI bajo tools/ y benchmarks procesan escenarios/datasets y producen reportes locales.

## Inputs

- scenarios
- seeds
- dataset records

## Outputs

- synthetic observations
- benchmark summaries
- manifests

## Dependencies

- Scenario Contract and Loader
- Python
- pytest

## Consumers

- investigadores
- mantenedores
- CI no bloqueante para benchmarks

## Data

- scenario corpora
- expected outputs
- narrative claim records

## APIs

- tool CLIs
- benchmark commands

## Failure Modes

- sobreinterpretación de sintéticos
- deriva de fixtures
- loader divergente
- resultado no reproducible

## Security

No debe contener datos sensibles ni atribuir resultados sintéticos a personas o instituciones reales.

## Tests

- `tests/test_scenario_mutator.py`
- `tests/test_scenario_telemetry.py`
- `tests/test_narrative_consistency.py`

## Deployment

No es un servicio; se ejecuta localmente o en CI como tooling.

## Source Files

- `tools/scenario_generator/`
- `tools/scenario_mutator.py`
- `tools/scenario_telemetry.py`
- `benchmarks/`

## Related Components

- [[Scenario Contract and Loader]]
- [[Scenario Data Model]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
