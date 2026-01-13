# WORKFLOWS — Merge / Deploy / Automatización

## Qué es “automatización” aquí (en humano)
Define qué proceso se dispara: tests, build, lint, generación de docs, releases, etc.

---

## Fix encoding / mojibake en docs (PowerShell)
Cuando veas mojibake (p. ej. Ã, â, ð, Â) en Markdown dentro de `docs/`, usa el fixer **en modo seguro**.

### 1) Preview (DryRun)
No toca archivos; lista qué cambiaría:
```powershell
powershell -ExecutionPolicy Bypass -File .\tools\fix_encoding_docs.ps1 -Path .\docs -DryRun
```

----

## Checklist PRE-MERGE
- [ ] Pull de main actualizado
- [ ] Snapshot de trazabilidad actualizado (`tools/trace_repo.ps1`)
- [ ] Tests pasan localmente
- [ ] Revisión de cambios en docs críticas (README/START_HERE)
- [ ] Workflows CI no cambian sin revisión
- [ ] Plan de rollback definido (revert vs reset)
- [ ] Changelog/STATUS actualizado


## Checklist PRE-DEPLOY (si existe deploy)
- [ ] Tag/versión definida
- [ ] Artefactos generados correctamente
- [ ] Variables/secretos verificados
- [ ] Monitoreo/logs listos
- [ ] Rollback confirmado

## Rollback cookbook
- Revert seguro:
- Reset + force (solo emergencia y con rulesets claros):

## Inventario actual de workflows
- .github/workflows/link-check.yml
  - Trigger: push, pull_request, workflow_dispatch
  - Accion: lycheeverse/lychee-action@v1
  - Alcance: README.md, CONTRIBUTING.md, docs/**/*.md, v1_core/**/*.md, legacy/**/*.md
  - Escribe en repo: no (solo lectura)

## Regla de cambio
- Cualquier cambio en `.github/workflows` se documenta en `docs/context/STATUS.md`.


---

