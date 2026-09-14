---
type: "component"
status: "partial"
layer: "infrastructure"
criticality: "high"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "ops/ec2/deploy-current.sh"
  - "ops/ec2/rollback-current.sh"
  - "ops/ec2/preflight-deploy.sh"
  - "ops/ec2/README.md"
tags:
  - "infrastructure"
  - "deployment"
  - "rollback"
---

# EC2 Release Operations

> **Estado:** `partial` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Preparar despliegues y rollbacks manuales con identidad exacta, validación y recuperación transaccional.

## Responsibilities

- Exigir ref explícito y resolverlo a commit completo.
- Validar candidato antes de cambiar current.
- Preservar provenance, rollback target y recovery logs.

## Runtime Behaviour

Los scripts crean releases gestionadas, verifican launcher y estado, cambian el symlink current de forma transaccional y requieren restart explícito del servicio.

## Inputs

- commit SHA o tag explícito
- host preflight

## Outputs

- managed release
- RELEASE_STATE
- ROLLBACK_STATE
- recovery evidence

## Dependencies

- Linux
- git
- Python
- systemd
- sha256sum
- host configuration

## Consumers

- operadores del host
- hub-core
- Local HTTP API

## Data

- release state
- rollback state
- launcher hash
- validation log

## APIs

- hub-ops CLI
- deploy-current
- rollback-current

## Failure Modes

- preflight fallido
- candidato inválido
- rollback target no atestado
- fallo de mutación/recovery

## Security

No usa defaults implícitos de branch/HEAD y falla cerrado; no prueba configuración cloud, red o credenciales externas.

## Tests

- `tests/test_ec2_deploy_hub_api_sync.py`
- `tests/test_ec2_legacy_adoption.py`
- `tests/test_ec2_preflight_and_evidence.py`

## Deployment

Código de operaciones manual; la existencia de scripts no certifica una instancia activa.

## Source Files

- `ops/ec2/deploy-current.sh`
- `ops/ec2/rollback-current.sh`
- `ops/ec2/preflight-deploy.sh`
- `ops/ec2/README.md`

## Related Components

- [[Operational Records]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
