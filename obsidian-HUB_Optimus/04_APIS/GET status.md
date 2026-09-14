---
type: "api"
status: "partial"
method: "GET"
route: "/status"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "ops/ec2/hub-api.sh"
tags:
  - "api"
  - "http"
  - "get-status"
---

# GET /status

## Purpose

Reportar identidad de proceso, release configurada y capacidades declaradas.

## Handler

`Handler.do_GET → product_status`

## Authentication

Ninguna en loopback.

## Authorization

No se expone por la configuración Nginx versionada.

## Input

Sin body.

## Output

Producto, running/configured release y commit, launcher SHA-256, release_state y capabilities.

## Side Effects

Lectura de symlink, git commit y RELEASE_STATE.

## Dependencies

- `ops/ec2/hub-api.sh`

## Error Behaviour

404 fuera de la ruta; campos vacíos cuando no se puede resolver estado.

## Consumers

- Inspección operativa local; no se identifica un cliente HTTP versionado que consuma la ruta.

## Source

- `ops/ec2/hub-api.sh`

## Deployment Boundary

La ruta está implementada en el árbol analizado. Esto no prueba que un servicio público o local esté activo. Véanse [[Interface Catalogue]] y [[Deployment Architecture]].

## Related Components

- [[Local HTTP API]]
