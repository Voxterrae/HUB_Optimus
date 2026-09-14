---
type: "component"
status: "active"
layer: "backend"
criticality: "high"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "scenario.schema.json"
  - "run_scenario.py"
tags:
  - "runtime"
  - "schema"
  - "validation"
---

# Scenario Contract and Loader

> **Estado:** `active` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Aceptar únicamente escenarios JSON que cumplan el contrato estructural y las invariantes de identidad.

## Responsibilities

- Leer UTF-8 y JSON estricto.
- Validar Draft 2020-12 y rechazar campos extra.
- Rechazar nombres de actores duplicados y clasificar errores controlados.

## Runtime Behaviour

run_scenario.py carga el schema, valida la estructura, aplica la unicidad de actores y construye un Scenario antes de invocar al simulador.

## Inputs

- archivo Scenario JSON
- scenario.schema.json

## Outputs

- Scenario validado
- errores parse/schema controlados

## Dependencies

- Python 3.11+
- jsonschema

## Consumers

- Scenario CLI
- Simulator
- scenario laboratory tools

## Data

- Scenario
- Actor role
- success criteria
- max rounds

## APIs

- Scenario CLI

## Failure Modes

- JSON inválido
- UTF-8 inválido
- schema inválido
- actor duplicado
- fallo de lectura/escritura

## Security

Reduce ambigüedad de entrada; no verifica hechos del mundo real ni calidad de política.

## Tests

- `tests/test_run_scenario_cli.py`
- `tests/test_scenario_loading.py`
- `tests/test_regression_runner.py`

## Deployment

Forma parte del runtime Python local y de releases EC2 cuando se instalan explícitamente.

## Source Files

- `scenario.schema.json`
- `run_scenario.py`

## Related Components

- [[Scenario Laboratory and Datasets]]
- [[Round-based Simulator]]
- [[Scenario CLI]]
- [[Scenario Data Model]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
