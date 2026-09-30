---
type: "api"
status: "partial"
method: "POST"
route: "/intake/url"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "ops/ec2/hub-api.sh"
  - "ops/ec2/controlled_url_intake.v1.schema.json"
  - "ops/ec2/nginx/operator-api.conf"
tags:
  - "api"
  - "http"
  - "post-intake-url"
---

# POST /intake/url

## Purpose

Recuperar y extraer texto de una URL pública bajo límites estrictos.

## Handler

`Handler.handle_url_intake`

## Authentication

Ninguna en el handler; Nginx limita CORS y rate, no autentica.

## Authorization

El handler no autoriza por principal. Nginx allowlistea la ruta; los límites de esquema, puerto e IP son controles de entrada y red.

## Input

`{"url":"<absolute ASCII http(s) URL>"}`; otros campos de aplicación se ignoran.

## Output

Success/error shape de controlled_url_intake.v1.schema.json.

## Side Effects

Una petición GET remota; no se documenta persistencia del body recuperado.

## Dependencies

- `ops/ec2/hub-api.sh`
- `ops/ec2/controlled_url_intake.v1.schema.json`
- `ops/ec2/nginx/operator-api.conf`

## Error Behaviour

400/414/415/422/502/503/504/508 según validación, red y extracción.

## Consumers

- No se confirma un consumidor browser activo en el Operator público actual; la ruta queda como contrato para callers controlados del host.

## Source

- `ops/ec2/hub-api.sh`
- `ops/ec2/controlled_url_intake.v1.schema.json`
- `ops/ec2/nginx/operator-api.conf`

## Deployment Boundary

La ruta está implementada en el árbol analizado. Esto no prueba que un servicio público o local esté activo. Véanse [[Interface Catalogue]] y [[Deployment Architecture]].

## Related Components

- [[Local HTTP API]]
- [[Controlled URL Intake]]
