---
type: "api"
status: "partial"
method: "GET"
route: "/health"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "ops/ec2/hub-api.sh"
  - "ops/ec2/nginx/operator-api.conf"
tags:
  - "api"
  - "http"
  - "get-health"
---

# GET /health

## Purpose

Comprobar que el proceso HTTP responde.

## Handler

`Handler.do_GET in generated hub_api.py`

## Authentication

Ninguna en el servicio local; la configuración Nginx puede exponer esta ruta.

## Authorization

No hay autorización por principal; Nginx limita la superficie a esta ruta y CORS no constituye autenticación.

## Input

Sin body.

## Output

`{"status":"ok"}`

## Side Effects

Ninguno documentado.

## Dependencies

- `ops/ec2/hub-api.sh`
- `ops/ec2/nginx/operator-api.conf`

## Error Behaviour

404 para rutas no reconocidas.

## Consumers

- Smoke/health checks locales documentados en `ops/ec2/`.
- Proxy Nginx opcional.

## Source

- `ops/ec2/hub-api.sh`
- `ops/ec2/nginx/operator-api.conf`

## Deployment Boundary

La ruta está implementada en el árbol analizado. Esto no prueba que un servicio público o local esté activo. Véanse [[Interface Catalogue]] y [[Deployment Architecture]].

## Related Components

- [[Local HTTP API]]
