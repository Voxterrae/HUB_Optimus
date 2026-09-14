---
type: "component"
status: "partial"
layer: "backend"
criticality: "high"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "ops/ec2/hub-api.sh"
  - "ops/ec2/hub-api.service"
  - "ops/ec2/hub-api-control.sh"
tags:
  - "backend"
  - "http-api"
  - "local-only"
---

# Local HTTP API

> **Estado:** `partial` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Exponer en loopback health, status, controlled intake y análisis local.

## Responsibilities

- Aplicar framing JSON estricto y límites de cuerpo.
- Delegar /analyze a hub-core con identidad exacta de run.
- Devolver respuestas JSON estables.

## Runtime Behaviour

Un HTTPServer síncrono escucha en 127.0.0.1:8080. /analyze crea un archivo temporal 0600, invoca hub-core y devuelve el resultado del run exacto.

## Inputs

- HTTP requests locales

## Outputs

- JSON health/status/intake/analyze

## Dependencies

- Python stdlib HTTPServer
- hub-core
- controlled intake

## Consumers

- clientes locales
- proxy Nginx limitado

## Data

- temporary CaseInput
- run identity
- status metadata

## APIs

- GET /health
- GET /status
- POST /intake/url
- POST /analyze

## Failure Modes

- body inválido
- run sin identidad
- tempfile no eliminable
- resultado ausente o inválido

## Security

Bind loopback, umbrales de cuerpo y JSON estricto. No implementa autenticación; la exposición pública debe mantenerse allowlisted.

## Tests

- `tests/test_hub_api_controlled_url_intake.py`
- `tests/test_ec2_deploy_hub_api_sync.py`

## Deployment

Launcher instalado manualmente en host Linux y controlado por systemd; no se attesta host vivo.

## Source Files

- `ops/ec2/hub-api.sh`
- `ops/ec2/hub-api.service`
- `ops/ec2/hub-api-control.sh`

## Related Components

- [[Local Control Prototype]]
- [[Controlled URL Intake]]
- [[EC2 Core Runner and Run Registry]]
- [[GET health]]
- [[GET status]]
- [[POST intake url]]
- [[POST analyze]]
- [[Operational Records]]
- [[Semantic Data Model]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
