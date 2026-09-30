---
type: "component"
status: "partial"
layer: "integration"
criticality: "high"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "ops/ec2/hub-api.sh"
  - "ops/ec2/controlled_url_intake.v1.schema.json"
  - "ops/ec2/nginx/operator-api.conf"
tags:
  - "integration"
  - "url-intake"
  - "ssrf-boundary"
---

# Controlled URL Intake

> **Estado:** `partial` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Recuperar una única URL pública con límites de red, tamaño y extracción, conservando estado no verificado.

## Responsibilities

- Validar URI, puerto, DNS e IP en cada salto.
- Fijar la conexión a IPs públicas validadas y limitar redirects/tiempo/tamaño.
- Extraer texto sin cookies, credenciales, automatización de navegador ni bypass.

## Runtime Behaviour

POST /intake/url valida una URL ASCII HTTP(S), realiza un GET acotado, extrae texto y devuelve procedencia con verification_status=unreviewed.

## Inputs

- {"url": "https://…"}

## Outputs

- Controlled URL intake response
- error response clasificado

## Dependencies

- Python standard library networking
- DNS resolver
- remote HTTP source

## Consumers

- Local HTTP API
- clientes controlados

## Data

- URL
- redirect chain
- retrieval metadata
- extracted text

## APIs

- POST /intake/url

## Failure Modes

- host bloqueado
- DNS no resoluble
- timeout
- content type no soportado
- redirect excesivo
- extracción vacía

## Security

Incluye defensas SSRF a nivel aplicación, pinning de IP y límites estrictos; la infraestructura de red y el resolver permanecen fuera de prueba.

## Tests

- `tests/test_hub_api_controlled_url_intake.py`
- `tests/test_ec2_operator_api_proxy_config.py`

## Deployment

Implementado dentro del launcher local; la configuración Nginx permite exponer solo esta ruta y health, pero el estado vivo es desconocido.

## Source Files

- `ops/ec2/hub-api.sh`
- `ops/ec2/controlled_url_intake.v1.schema.json`
- `ops/ec2/nginx/operator-api.conf`

## Related Components

- [[Local HTTP API]]
- [[POST intake url]]
- [[Data Architecture]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
