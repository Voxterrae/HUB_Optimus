---
type: "cli-interface"
status: "partial"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "ops/ec2/hub-core.sh"
tags:
  - "api"
  - "cli"
  - "hub-core-cli"
---

# hub-core CLI

## Purpose

Ejecutar el core contra la release actual y registrar runs.

## Command

```bash
hub-core status|test|benchmark|narrative-benchmark|semantic-smoke|scenario-smoke|analyze
```

## Input

Subcommand y case path cuando corresponde.

## Output

Run directory, logs y resultados.

## Error Behaviour

Falla si current, venv, input o runtime no están disponibles.

## Side Effects

Puede crear archivos de salida o directorios de run según la opción/comando.

## Source

- `ops/ec2/hub-core.sh`

## Related Components

- [[EC2 Core Runner and Run Registry]]
- [[Operational Records]]

## Boundary

La interfaz ejecuta únicamente el comportamiento documentado por su fuente y tests; no añade capacidades de producto ni prueba un deployment externo.
