---
type: "component"
status: "partial"
layer: "backend"
criticality: "high"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "semantic_engine/contracts/case_input.schema.json"
  - "semantic_engine/contracts/case_input.py"
  - "semantic_engine/contracts/analysis_result.py"
  - "semantic_engine/cli/__main__.py"
tags:
  - "semantic-engine"
  - "contracts"
  - "cli"
---

# Semantic Engine Contracts and CLI

> **Estado:** `partial` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Validar CaseInput v1 y ensamblar un AnalysisResult determinista para revisión.

## Responsibilities

- Validar forma y referencias cruzadas de claims y evidence.
- Preservar inferences, uncertainties, narrative amplification y operational signal.
- Serializar JSON estricto sin añadir scoring ni model judging.

## Runtime Behaviour

La CLI analyze lee un CaseInput, aplica schema e invariantes, construye dataclasses inmutables y escribe el resultado a stdout o archivo.

## Inputs

- CaseInput v1 JSON

## Outputs

- AnalysisResult JSON
- errores controlados

## Dependencies

- Python 3.11+
- jsonschema

## Consumers

- hub-core
- Local HTTP API
- operadores humanos

## Data

- ClaimRecord
- EvidenceRecord
- AnalysisResult
- DecisionTrace
- AuditLogEntry

## APIs

- Semantic Engine CLI
- POST /analyze mediante hub-core

## Failure Modes

- campos desconocidos
- IDs duplicados
- referencias huérfanas
- JSON no finito
- salida no serializable

## Security

No adjudica verdad, no puntúa personas y no sustituye revisión humana.

## Tests

- `tests/semantic_engine/test_case_input_validation.py`
- `tests/semantic_engine/test_cli_smoke.py`

## Deployment

CLI local; hub-core puede invocarla dentro de una release EC2 instalada.

## Source Files

- `semantic_engine/contracts/case_input.schema.json`
- `semantic_engine/contracts/case_input.py`
- `semantic_engine/contracts/analysis_result.py`
- `semantic_engine/cli/__main__.py`

## Related Components

- [[EC2 Core Runner and Run Registry]]
- [[Operator PWA]]
- [[Semantic Engine CLI]]
- [[POST analyze]]
- [[Semantic Data Model]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
