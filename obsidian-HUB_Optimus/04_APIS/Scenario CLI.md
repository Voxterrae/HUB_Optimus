---
type: "cli-interface"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "run_scenario.py"
  - "scenario.schema.json"
tags:
  - "api"
  - "cli"
  - "scenario-cli"
---

# Scenario CLI

## Purpose

Validar y ejecutar un escenario determinista.

## Command

```bash
python run_scenario.py <scenario.json> [--seed N] [--policy NAME] [--output PATH]
```

## Input

Scenario JSON

## Output

SimulationResult JSON

## Error Behaviour

exit 2 para errores controlados de input/output.

## Side Effects

Puede crear archivos de salida o directorios de run según la opción/comando.

## Source

- `run_scenario.py`
- `scenario.schema.json`

## Related Components

- [[Scenario Contract and Loader]]
- [[Round-based Simulator]]
- [[Scenario Data Model]]

## Boundary

La interfaz ejecuta únicamente el comportamiento documentado por su fuente y tests; no añade capacidades de producto ni prueba un deployment externo.
