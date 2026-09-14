---
type: "cli-interface"
status: "partial"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "semantic_engine/cli/__main__.py"
  - "semantic_engine/contracts/case_input.py"
tags:
  - "api"
  - "cli"
  - "semantic-engine-cli"
---

# Semantic Engine CLI

## Purpose

Validar CaseInput y ensamblar AnalysisResult.

## Command

```bash
python -m semantic_engine.cli analyze <case.json> [--output PATH]
```

## Input

CaseInput v1 JSON

## Output

AnalysisResult JSON

## Error Behaviour

exit 1 para errores esperados.

## Side Effects

Escribe stdout contractual o un archivo cuando se usa --output.

## Source

- `semantic_engine/cli/__main__.py`
- `semantic_engine/contracts/case_input.py`

## Related Components

- [[Semantic Engine Contracts and CLI]]
- [[Semantic Data Model]]

## Boundary

La interfaz ejecuta únicamente el comportamiento documentado por su fuente y tests; no añade capacidades de producto ni prueba un deployment externo.
