# STATUS — fuente de verdad operativa

## Hoy (2026-01-08)
- Hecho:
  - [ ] (Ej: Se creó el pack de contexto en /docs/context)
  - [ ] (Ej: Se hizo merge que activó automatizaciones y hubo reroll)
- Problemas:
  - (Ej: Workflows se dispararon y cambiaron README/Docs inesperadamente)
  - (Ej: Hubo errores en pipeline / actions / outputs)
- Decisiones:
  - (Ej: Rollback vía revert, NO reset/force salvo emergencia)

## Prioridades (Top 5)
1) Documentar qué workflow se disparó y por qué.
2) Checklist pre-merge/pre-deploy para evitar repetir el susto.
3) Definir “qué es core” vs “docs/simulaciones” vs “legacy”.
4) Congelar reglas de merge (branch protection / required checks).
5) Preparar “runbook de rollback” (revert vs reset).

## Riesgos / cosas frágiles
- Cambios en `.github/workflows` pueden modificar el repo “sin que te enteres” (CI generando archivos).
- Docs multilenguaje pueden desincronizarse si el pipeline regenera contenido.

## Próximo merge/de
