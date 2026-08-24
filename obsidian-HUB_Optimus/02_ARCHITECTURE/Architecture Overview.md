---
type: "architecture"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "architecture"
  - "overview"
---

# Architecture Overview

## Architectural Character

HUB_Optimus es un **repository system** con múltiples programas y planos de autoridad. No existe una aplicación monolítica que cargue todo el contenido.

## Layers

| Layer | Components | Boundary |
| --- | --- | --- |
| Human governance | [[Governance Guardrails]] | Constriñe cambios; no ejecuta requests. |
| Methodology | [[Canonical v1 Methodology]] | Guía humanos; no se importa como policy. |
| Frontend | [[Public Static Site]], [[Operator PWA]] | Estático/local-first. |
| Scenario runtime | [[Scenario Contract and Loader]], [[Round-based Simulator]] | Simulación determinista y mínima. |
| Semantic runtime | [[Semantic Engine Contracts and CLI]] | Validación + assembly, no judging. |
| Local service | [[Local HTTP API]], [[Controlled URL Intake]], [[EC2 Core Runner and Run Registry]] | Loopback/host controlado. |
| Operations | [[EC2 Release Operations]], [[GitHub Pages Pipeline]] | Dos vías separadas de entrega. |
| Research | [[Scenario Laboratory and Datasets]] | Sintético/experimental. |
| Quality | [[Tests and Quality Gates]] | Evidencia acotada, no certificación externa. |

## Architectural Principles Observed

1. **Fail closed** para JSON, identidad de run, release provenance y controlled intake.
2. **Explicit boundaries** entre documentación, metodología, runtime y deployment.
3. **Local-first** para Operator y aprendizaje.
4. **Exact identity** mediante commit SHA, hashes y run IDs.
5. **Progressive enhancement** en el sitio estático.
6. **Human authority** para ratificación, merge y decisiones.

## Integration Reality

### Confirmed integrations

- Loader → Simulator.
- hub-core → Semantic Engine CLI.
- Local HTTP API → hub-core y controlled intake.
- Pages workflow → `site/` artifact.
- Operator → local learning store.

### Conditional or external integrations

- Nginx → Local HTTP API: configuración fuente confirmada; deployment desconocido.
- GitHub Pages runtime → public routes: requiere verificación del run concreto.
- EC2 host → local API: runbook/source confirmados; host vivo desconocido.
- Operator → backend: no debe asumirse como conexión pública activa.

## Documentation Drift

Véase [[Evidence Index#Documentation Drift|Documentation Drift]]. Los documentos derivados de julio siguen siendo útiles, pero no sustituyen el árbol actual de agosto.

## Related

- [[System Context]]
- [[Runtime Architecture]]
- [[Architecture Data Flow]]
- [[Dependency Graph]]
- [[Architecture Map]]
