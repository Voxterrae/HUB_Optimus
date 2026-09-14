---
type: "component"
status: "partial"
layer: "operations"
criticality: "high"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "ops/ec2/hub-core.sh"
  - "ops/ec2/hub-runs.sh"
  - "ops/ec2/README.md"
tags:
  - "operations"
  - "runs"
  - "provenance"
---

# EC2 Core Runner and Run Registry

> **Estado:** `partial` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Ejecutar comandos del core contra una release fijada y registrar cada run con identidad reproducible.

## Responsibilities

- Fijar el current release y commit antes de ejecutar.
- Crear directorios de run exclusivos y RUN_STATE.
- Ejecutar tests, benchmarks, smoke tests y semantic analyze.

## Runtime Behaviour

hub-core.sh resuelve /opt/hub-optimus/current, activa su venv, crea un run ID UTC con sufijo aleatorio y almacena artefactos bajo shared/runs.

## Inputs

- comando hub-core
- CaseInput o Scenario cuando corresponda

## Outputs

- run directory
- RUN_STATE
- logs y result JSON

## Dependencies

- Linux shell
- git
- Python venv
- pytest
- Semantic Engine
- Scenario Runtime

## Consumers

- Local HTTP API
- operadores del host

## Data

- RUN_STATE
- analysis_result.json
- benchmark logs

## APIs

- hub-core CLI

## Failure Modes

- current symlink ausente
- venv ausente
- input inexistente
- comando runtime fallido

## Security

umask 077 y rutas de run separadas; la revisión/autorización del ref desplegado sigue siendo humana.

## Tests

- `tests/test_ec2_run_identity_and_provenance.py`
- `tests/test_ec2_runbook_attestation.py`

## Deployment

Script instalado manualmente bajo shared/bin en el host EC2 documentado.

## Source Files

- `ops/ec2/hub-core.sh`
- `ops/ec2/hub-runs.sh`
- `ops/ec2/README.md`

## Related Components

- [[Local HTTP API]]
- [[Semantic Engine Contracts and CLI]]
- [[hub-core CLI]]
- [[Operational Records]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
