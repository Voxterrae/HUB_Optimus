---
type: "project"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "project"
  - "overview"
---

# Project Overview

## Definition

HUB_Optimus es un repositorio gobernado que reúne:

1. [[Governance Guardrails]] para autoridad, revisión y fuente de verdad.
2. [[Canonical v1 Methodology]] para trabajo humano estructurado.
3. Prototipos ejecutables y contratos acotados.
4. Datasets, benchmarks y tooling experimental.
5. Un sitio público estático, Operator y vías de operación local.
6. Evidencia reproducible mediante tests, commits y registros.

## Purpose

La finalidad es ayudar a estructurar información compleja, separar claims de evidence e inference, hacer visibles incertidumbres e incentivos y apoyar revisión humana preventiva.

## Scope

### Dentro del scope confirmado

- Scenario JSON validation y simulación determinista.
- CaseInput/AnalysisResult contracts y CLI.
- Operator local-first y learning candidate store no canónico.
- Controlled URL intake y API local.
- Scripts gestionados de release/rollback.
- Static Pages, workflows, tests y documentación.

### Fuera del scope confirmado

- Evaluación autónoma de verdad.
- Predicción real.
- Decisión o gobernanza autónoma.
- Servicio público autenticado del Semantic Engine.
- HERMES/enterprise/post-quantum en producción.
- Certificación permanente de deployments, settings o infraestructura.

## Product versus Repository

El repositorio es más amplio que cualquier programa individual. Las superficies ejecutables no deben agruparse como si formaran un único servicio integrado en producción.

| Plane | Meaning |
| --- | --- |
| Governance | Reglas humanas y registros de decisión. |
| Methodology | Método humano canónico, más amplio que el código. |
| Runtime | Programas y contratos concretos. |
| Data | Schemas, fixtures, runs, datasets y evidencia. |
| Delivery | Pages workflow y scripts de host gestionado. |
| External state | GitHub settings, deployment, DNS, TLS, host y servicios vivos. |

## Current Baseline

- Commit: `30e985226347b4bc59b0e187b96633a09647ca42`
- Tree: `fabb9da1fdb6979df0bc764017752f118088e69f`
- Analysis: `2026-08-21`
- Issue de trabajo: `#1901`

## Related

- [[Current State]]
- [[Architecture Overview]]
- [[Capabilities]]
- [[Limitations]]
- [[Repository Analysis]]
