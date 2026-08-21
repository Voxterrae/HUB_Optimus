---
type: "component"
status: "experimental"
layer: "experimental"
criticality: "low"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "hub_optimus/hub_optimus_control.py"
tags:
  - "experimental"
  - "control-plane"
  - "isolated"
---

# Local Control Prototype

> **Estado:** `experimental` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Demostrar un allowlist actor→tool y un log de inspección en memoria.

## Responsibilities

- Evaluar nombres de actor y tool contra una policy simple.
- Ejecutar únicamente sum y echo.
- Registrar intentos en memoria con snapshots seguros.

## Runtime Behaviour

PolicyEngine y ControlPlane operan en un único proceso. Ninguna superficie soportada los importa.

## Inputs

- actor string
- tool name
- argumentos built-in acotados

## Outputs

- tool result
- inspection log
- errores Permission/Value

## Dependencies

- Python standard library

## Consumers

- uso educativo local

## Data

- in-memory call log

## APIs

- Python classes

## Failure Modes

- interpretar actor string como identidad
- confundir log en memoria con auditoría durable
- usar como gateway de producción

## Security

Explícitamente no implementa autenticación, autorización de producción, OPA, SPIFFE, OpenTelemetry ni auditoría durable.

## Tests

- `tests/test_hub_optimus_control.py`

## Deployment

No desplegado ni conectado al runtime soportado.

## Source Files

- `hub_optimus/hub_optimus_control.py`

## Related Components

- [[Local HTTP API]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
