---
type: "component"
status: "active"
layer: "governance"
criticality: "high"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md"
  - "config/governance/owner_identity.v1.json"
  - "docs/context/SOURCE_OF_TRUTH.md"
  - "docs/context/OWNER_AUTHORITY_HANDOFF.md"
  - ".github/CODEOWNERS"
tags:
  - "governance"
  - "authority"
  - "source-of-truth"
---

# Governance Guardrails

> **Estado:** `active` · **Evidencia:** `CONFIRMED` · **Baseline:** `30e985226347`

## Purpose

Define la autoridad humana, la jerarquía de fuentes y las puertas de cambio del repositorio.

## Responsibilities

- Mantener la autoridad final y la propiedad separadas de la capacidad técnica de contribuir.
- Exigir cambios visibles, revisables y trazables mediante Issues, Pull Requests y checks.
- Resolver conflictos entre documentación, código, tests y estado mutable de GitHub.

## Runtime Behaviour

No forma parte de las rutas de ejecución del simulador, Semantic Engine ni Operator. Restringe el proceso humano de cambio y revisión.

## Inputs

- Propuestas humanas
- Issues y Pull Requests
- commits y checks
- evidencia del repositorio

## Outputs

- decisiones humanas trazables
- límites de autoridad
- estado de revisión

## Dependencies

- GitHub
- owner identity record
- protected review process

## Consumers

- Contribuidores
- mantenedores
- agentes de IA
- revisores

## Data

- owner_identity.v1.json
- records de Issue/PR/checks

## APIs

- GitHub review workflow

## Failure Modes

- confundir una propuesta con una ratificación
- usar chat como autorización
- aceptar evidencia obsoleta

## Security

Falla cerrado para cambios protegidos y exige identidad, historial verificado y revisión humana.

## Tests

- `tests/test_founder_authority_guard.py`
- `tests/test_founder_authority_workflow.py`

## Deployment

No se despliega como servicio; se aplica mediante archivos versionados y controles de GitHub.

## Source Files

- `docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md`
- `config/governance/owner_identity.v1.json`
- `docs/context/SOURCE_OF_TRUTH.md`
- `docs/context/OWNER_AUTHORITY_HANDOFF.md`
- `.github/CODEOWNERS`

## Related Components

- [[Architecture Overview]]

## Evidence Boundary

Esta nota describe el árbol fijado por [[Repository Analysis]]. La presencia de código o configuración no certifica un deployment, setting o servicio externo vivo. Véase [[Status Definitions]].
