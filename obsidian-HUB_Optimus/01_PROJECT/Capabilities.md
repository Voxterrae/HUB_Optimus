---
type: "capability-map"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "capabilities"
  - "status"
---

# Capabilities

## Evidence-backed Map

| Capability / component | Status | Verified boundary | Evidence |
| --- | --- | --- | --- |
| [[Governance Guardrails]] | `active` | Define la autoridad humana, la jerarquía de fuentes y las puertas de cambio del repositorio. | CONFIRMED |
| [[Canonical v1 Methodology]] | `active` | Proporcionar el marco humano de evaluación estructurada, incentivos, verificación, secuencia y estabilidad. | CONFIRMED |
| [[Scenario Contract and Loader]] | `active` | Aceptar únicamente escenarios JSON que cumplan el contrato estructural y las invariantes de identidad. | CONFIRMED |
| [[Round-based Simulator]] | `active` | Ejecutar una simulación determinista y acotada de rondas con políticas simples. | CONFIRMED |
| [[Semantic Engine Contracts and CLI]] | `partial` | Validar CaseInput v1 y ensamblar un AnalysisResult determinista para revisión. | CONFIRMED |
| [[Operator PWA]] | `partial` | Preparar en el navegador intake estructurado, borradores con procedencia y una revisión humana local. | CONFIRMED |
| [[Operator Learning Store]] | `partial` | Persistir candidatos de aprendizaje locales, versionados y revisados por humanos sin convertirlos en memoria canónica. | CONFIRMED |
| [[Controlled URL Intake]] | `partial` | Recuperar una única URL pública con límites de red, tamaño y extracción, conservando estado no verificado. | CONFIRMED |
| [[Local HTTP API]] | `partial` | Exponer en loopback health, status, controlled intake y análisis local. | CONFIRMED |
| [[EC2 Core Runner and Run Registry]] | `partial` | Ejecutar comandos del core contra una release fijada y registrar cada run con identidad reproducible. | CONFIRMED |
| [[EC2 Release Operations]] | `partial` | Preparar despliegues y rollbacks manuales con identidad exacta, validación y recuperación transaccional. | CONFIRMED |
| [[Public Static Site]] | `active` | Presentar la identidad pública, límites del proyecto, documentación y acceso al Operator mediante una experiencia estática. | CONFIRMED |
| [[GitHub Pages Pipeline]] | `active` | Publicar exactamente el árbol site/ en GitHub Pages tras cambios aprobados en main. | CONFIRMED |
| [[Scenario Laboratory and Datasets]] | `experimental` | Generar, mutar, medir y comparar escenarios y datasets sintéticos de forma reproducible. | CONFIRMED |
| [[Tests and Quality Gates]] | `active` | Reducir regresiones mediante pytest, checks de encoding, contratos estáticos y workflows fijados. | CONFIRMED |
| [[Local Control Prototype]] | `experimental` | Demostrar un allowlist actor→tool y un log de inspección en memoria. | CONFIRMED |

## Interpretation

- `active` significa que la superficie existe y está operativa dentro de su contrato acotado; no implica completitud de producto.
- `partial` significa que hay código/contratos/tests, pero integración, alcance o deployment son incompletos o no verificados.
- `experimental` identifica tooling o prototipos que no deben convertirse en claims de producto.
- El estado externo de Pages, EC2, DNS, TLS y Nginx permanece separado.

## Main Runnable Capabilities

### Scenario runtime

[[Scenario Contract and Loader]] + [[Round-based Simulator]].

### Semantic records

[[Semantic Engine Contracts and CLI]].

### Browser review

[[Operator PWA]] + [[Operator Learning Store]].

### Local backend

[[Local HTTP API]], [[Controlled URL Intake]] y [[EC2 Core Runner and Run Registry]].

### Delivery

[[Public Static Site]], [[GitHub Pages Pipeline]] y [[EC2 Release Operations]].

## Proposed or Non-implemented

Los RFC y documentos de visión no se elevan aquí a capacidad. Véase [[Limitations]] y [[Evidence Index#Explicit non-capabilities|Explicit non-capabilities]].
