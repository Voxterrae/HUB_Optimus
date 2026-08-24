---
type: "component"
status: "active"
layer: "backend"
criticality: "high"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "hub_optimus_simulator.py"
  - "benchmarks/run_benchmarks.py"
tags:
  - "runtime"
  - "simulation"
  - "determinism"
---

# Round-based Simulator

> **Estado:** `active` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Ejecutar una simulación determinista y acotada de rondas con políticas simples.

## Responsibilities

- Crear actores desde roles validados.
- Ejecutar políticas uniformes, sesgadas o personalizadas.
- Registrar historial y detenerse al cumplir una coincidencia exacta de criterio.

## Runtime Behaviour

Simulator.run crea un random.Random aislado, ejecuta actores por ronda y devuelve success o failure con historial y detalle.

## Inputs

- Scenario validado
- seed opcional
- policy opcional

## Outputs

- SimulationResult JSON

## Dependencies

- Python standard library
- Scenario Contract and Loader

## Consumers

- Scenario CLI
- benchmarks
- laboratory tools

## Data

- Scenario
- Actor
- action history
- SimulationResult

## APIs

- Scenario CLI

## Failure Modes

- criterio inalcanzable
- política inválida
- supuestos sintéticos interpretados como realidad

## Security

No toma decisiones reales, no predice y no ejecuta la metodología completa.

## Tests

- `tests/test_smoke.py`
- `tests/test_simulator_isolation.py`
- `tests/test_policy_variation.py`

## Deployment

Runtime Python local; puede ejecutarse por hub-core en una release instalada.

## Source Files

- `hub_optimus_simulator.py`
- `benchmarks/run_benchmarks.py`

## Related Components

- [[Canonical v1 Methodology]]
- [[Scenario Contract and Loader]]
- [[Scenario CLI]]
- [[Scenario Data Model]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
