---
type: "api"
status: "partial"
method: "POST"
route: "/analyze"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "ops/ec2/hub-api.sh"
  - "ops/ec2/hub-core.sh"
  - "semantic_engine/cli/__main__.py"
tags:
  - "api"
  - "http"
  - "post-analyze"
---

# POST /analyze

## Purpose

Ejecutar Semantic Engine sobre un CaseInput a través de hub-core.

## Handler

`Handler.handle_analyze`

## Authentication

Ninguna en loopback.

## Authorization

No se expone por la configuración Nginx versionada.

## Input

CaseInput v1 JSON, máximo 64,000 bytes en el handler.

## Output

`{"status":"ok","run_id":"…","run_path":"…","analysis_result":{…}}`.

## Side Effects

Tempfile 0600, run directory, RUN_STATE y analysis_result.json; el tempfile se elimina.

## Dependencies

- `ops/ec2/hub-api.sh`
- `ops/ec2/hub-core.sh`
- `semantic_engine/cli/__main__.py`

## Error Behaviour

400/411/413 framing; 500 ante ejecución, identidad, cleanup o resultado inválido.

## Consumers

- No public consumer is identified in the tree; the route is intended for local controlled callers.

## Source

- `ops/ec2/hub-api.sh`
- `ops/ec2/hub-core.sh`
- `semantic_engine/cli/__main__.py`

## Deployment Boundary

La ruta está implementada en el árbol analizado. Esto no prueba que un servicio público o local esté activo. Véanse [[Interface Catalogue]] y [[Deployment Architecture]].

## Related Components

- [[Local HTTP API]]
- [[Semantic Engine Contracts and CLI]]
- [[EC2 Core Runner and Run Registry]]
