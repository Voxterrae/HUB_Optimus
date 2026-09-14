---
type: "current-state"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "current-state"
  - "onboarding"
  - "operations"
---

# Current State

## Qué hace el proyecto

HUB_Optimus es una metodología versionada, un corpus de gobierno humano y un conjunto de prototipos para estructurar escenarios, afirmaciones, evidencia, incertidumbre y revisión. No es todavía un único producto SaaS ni un motor autónomo de verdad.

## Qué funciona en el árbol analizado

- [[Scenario Contract and Loader]] valida JSON estricto, schema e identidad de actores.
- [[Round-based Simulator]] ejecuta rondas deterministas con políticas simples.
- [[Semantic Engine Contracts and CLI]] valida CaseInput y ensambla AnalysisResult.
- [[Operator PWA]] prepara borradores y revisión local.
- [[Operator Learning Store]] persiste candidatos locales no canónicos en IndexedDB.
- [[Controlled URL Intake]] implementa fetch/extraction acotados con provenance `unreviewed`.
- [[Local HTTP API]] expone cuatro rutas en loopback.
- [[EC2 Release Operations]] contiene deploy/rollback manual con provenance.
- [[Public Static Site]] y [[GitHub Pages Pipeline]] contienen la vía estática de publicación.
- [[Tests and Quality Gates]] cubre contratos, regresiones, encoding, workflows y PowerShell.

## Cómo está organizado

```text
Governance + Source of Truth
        ↓
Methodology / Human workflow
        ↓
Executable prototypes
        ├── Scenario runtime
        ├── Semantic Engine CLI
        ├── Operator PWA
        ├── Local HTTP API
        └── EC2 operations
        ↓
Schemas, datasets, tests and evidence records
        ↓
Static Pages and optional managed host
```

Abrir [[Architecture Map]].

## Qué está incompleto o no verificado

- No hay truth adjudication, prediction, model judge ni ejecución completa de la metodología.
- No hay Semantic Engine público autenticado.
- HERMES, enterprise y post-quantum siguen fuera del runtime implementado.
- Pages, EC2, DNS, TLS, Nginx y repository settings son estado mutable externo.
- Las traducciones no canónicas tienen madurez desigual.
- El vault es un snapshot; no se regenera automáticamente.

## Cómo se ejecuta

### Scenario runtime

```bash
python run_scenario.py example_scenario.json --seed 42
```

### Semantic Engine

```bash
python -m semantic_engine.cli analyze examples/semantic_engine/case_minimal.json
```

### Local host operations

```bash
hub-core status
hub-core semantic-smoke
hub-core scenario-smoke
hub-core analyze /path/to/case.json
```

Los últimos comandos requieren una instalación gestionada; la fuente no prueba que exista.

## Cómo se prueba

```bash
python -m pytest -q
python benchmarks/run_benchmarks.py
python benchmarks/run_narrative_benchmarks.py
python tools/check_mojibake.py .
```

PowerShell requiere su job dedicado. Véase [[Testing Strategy]].

## Cómo se despliega

- Pages: merge aprobado en `main` → workflow → artifact `site/` → Pages.
- Host gestionado: ref explícito → preflight → candidate validation → current switch → restart explícito.

Véase [[Deployment Architecture]].

## Riesgos prioritarios

1. Deriva entre documentación histórica y árbol actual.
2. Confundir visión/metodología con capacidades implementadas.
3. Interpretar borradores o intake como evidencia verificada.
4. Exponer una API local sin una frontera autenticada.
5. Confiar en estado externo no inspeccionado.

Abrir [[Risk Register]].

## Dónde mirar para continuar

- Arquitectura: [[Architecture Overview]]
- Código por concepto: [[Source Map]]
- Contratos: [[Data Architecture]] y [[Interface Catalogue]]
- Operaciones: [[Operations Guide]]
- Seguridad: [[Security Boundaries]]
- Evidencia y discrepancias: [[Evidence Index]]
- Actualización del modelo: [[Update Protocol]]
