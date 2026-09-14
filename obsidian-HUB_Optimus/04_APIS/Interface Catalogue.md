---
type: "interface-catalogue"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "api"
  - "cli"
  - "interfaces"
---

# Interface Catalogue

## HTTP Interfaces

La implementación HTTP vive dentro del launcher generado por `ops/ec2/hub-api.sh` y escucha por defecto en `127.0.0.1:8080`.

| Interface | Status | Purpose | Evidence |
| --- | --- | --- | --- |
| [[GET health]] | `partial` | Comprobar que el proceso HTTP responde. | CONFIRMED |
| [[GET status]] | `partial` | Reportar identidad de proceso, release configurada y capacidades declaradas. | CONFIRMED |
| [[POST intake url]] | `partial` | Recuperar y extraer texto de una URL pública bajo límites estrictos. | CONFIRMED |
| [[POST analyze]] | `partial` | Ejecutar Semantic Engine sobre un CaseInput a través de hub-core. | CONFIRMED |

### Public exposure boundary

La configuración Nginx versionada permite únicamente:

- `GET /health`
- `POST /intake/url`

No permite `/status`, `/analyze`, runs, files, shell ni rutas arbitrarias. La configuración fuente está confirmada; su deployment vivo es `UNKNOWN`.

## CLI Interfaces

| Interface | Status | Command |
| --- | --- | --- |
| [[Scenario CLI]] | `active` | `python run_scenario.py <scenario.json> [--seed N] [--policy NAME] [--output PATH]` |
| [[Semantic Engine CLI]] | `partial` | `python -m semantic_engine.cli analyze <case.json> [--output PATH]` |
| [[hub-core CLI]] | `partial` | `hub-core status|test|benchmark|narrative-benchmark|semantic-smoke|scenario-smoke|analyze` |

## API Design Observations

- JSON estricto y límites de body.
- No autenticación en la API loopback.
- Identity de run exacta para `/analyze`.
- Controlled intake conserva `unreviewed`.
- Las rutas HTTP no constituyen un API público general.
- Los CLIs son la frontera ejecutable primaria y más verificable.

## Related

- [[Local HTTP API]]
- [[Runtime Architecture]]
- [[Security Boundaries]]
- [[Source Map]]
