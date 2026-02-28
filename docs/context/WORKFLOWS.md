# WORKFLOWS — Merge / Deploy / Automatización

## Qué es "automatización" aquí (en humano)
Define qué proceso se dispara: tests, build, lint, generación de docs, releases, etc.

---

## Fix encoding / mojibake en docs (PowerShell)
Cuando veas texto corrupto o caracteres rotos en Markdown dentro de `docs/`, usa el fixer **en modo seguro**.
Regla de codificación: todos los `.md` deben guardarse en **UTF-8**.

### 1) Preview (DryRun)
No toca archivos; lista qué cambiaría:
```powershell
powershell -ExecutionPolicy Bypass -File .\tools\fix_encoding_docs.ps1 -Path .\docs -DryRun
```

### 2) Guard local de mojibake
Para validar antes de abrir PR:
```powershell
python tools/check_mojibake.py
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
- .github/workflows/ci.yml
  - Trigger: pull_request, push (main)
  - Pasos: mojibake guard (`v1_core docs README.md CONTRIBUTING.md`), pytest
  - Escribe en repo: no (solo lectura)

- .github/workflows/link-check.yml
  - Trigger: push, pull_request, workflow_dispatch
  - Accion: lycheeverse/lychee-action@v1
  - Alcance: README.md, CONTRIBUTING.md, docs/**/*.md, v1_core/**/*.md, legacy/**/*.md
  - Escribe en repo: no (solo lectura)

- .github/workflows/repo_maintenance_bot.yml
  - Trigger: schedule (06:15 UTC daily), workflow_dispatch (mode: hygiene/i18n/full), pull_request (docs/**, v1_core/**, .github/workflows/**, tools/**)
  - Pasos: kernel_guard, maintenance_bot, pr_pro
  - Escribe en repo: sí (crea PRs de mantenimiento automático)
  - Requiere secrets: GH_APP_ID, GH_APP_PRIVATE_KEY (si no están configurados, el workflow se salta limpiamente)

## Regla de cambio
- Cualquier cambio en `.github/workflows` se documenta en `docs/context/STATUS.md`.


---
