---
type: "component"
status: "active"
layer: "testing"
criticality: "high"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - ".github/workflows/ci.yml"
  - "tests/"
  - "tools/check_mojibake.py"
tags:
  - "testing"
  - "ci"
  - "quality"
---

# Tests and Quality Gates

> **Estado:** `active` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Reducir regresiones mediante pytest, checks de encoding, contratos estáticos y workflows fijados.

## Responsibilities

- Ejecutar tests Python y pruebas de comportamiento PowerShell.
- Verificar mojibake, narrativa y action pins.
- Mantener benchmarks como señal separada de checks bloqueantes.

## Runtime Behaviour

CI instala requirements-dev, ejecuta checks de consistencia y pytest; un job separado prueba tooling PowerShell y benchmarks son no bloqueantes.

## Inputs

- repository tree
- fixtures
- expected outputs

## Outputs

- check status
- logs
- benchmark summary

## Dependencies

- GitHub Actions
- Python 3.12
- pytest
- PowerShell 7
- Node para probes estáticos

## Consumers

- Pull Requests
- mantenedores
- owner review

## Data

- test fixtures
- expected snapshots
- check results

## APIs

- CI workflow
- python -m pytest -q

## Failure Modes

- test no cubre claim
- check externo no ejecutado
- benchmark no bloqueante interpretado como gate

## Security

Un check verde prueba solo su contrato; no sustituye revisión ni certifica servicios externos.

## Tests

- `tests/`

## Deployment

Se ejecuta en GitHub Actions y localmente; no despliega el producto.

## Source Files

- `.github/workflows/ci.yml`
- `tests/`
- `tools/check_mojibake.py`

## Related Components

- [[Architecture Overview]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
