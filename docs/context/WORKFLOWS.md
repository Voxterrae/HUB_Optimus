# WORKFLOWS - Merge / Deploy / Automatizacion

## Que es automatizacion aqui
Procesos repetibles que se ejecutan por evento (push, pull_request, workflow_dispatch):
- tests
- link-check
- guardas de rutas sensibles
- mantenimiento de estructura/docs

---

## Link-check local (Lychee)
Ejecuta esto desde la raiz del repo para reproducir el chequeo localmente:

```powershell
lychee --config .github/lychee.toml README.md CONTRIBUTING.md docs/**/*.md v1_core/**/*.md
```

Notas:
- Este comando replica el alcance del workflow de link-check.
- En CI usamos `lycheeverse/lychee-action@v1`.

---

## Fix encoding / mojibake en docs (PowerShell)
Cuando veas mojibake (por ejemplo `Ã`, `â`, `ð`, `Â`) en markdown dentro de `docs/`, usa el fixer en modo seguro.

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\fix_encoding_docs.ps1 -Path .\docs -DryRun
```

---

## Checklist PRE-MERGE
- [ ] Pull de `main` actualizado
- [ ] Snapshot de trazabilidad actualizado (`tools/trace_repo.ps1`)
- [ ] Tests pasan localmente
- [ ] Link-check local en verde (Lychee)
- [ ] Revision de cambios en docs criticas (README/START_HERE)
- [ ] Cambios en `.github/workflows` documentados en `docs/context/STATUS.md`
- [ ] Plan de rollback definido

## Checklist PRE-DEPLOY (si aplica)
- [ ] Tag/version definida
- [ ] Artefactos generados correctamente
- [ ] Variables/secretos verificados
- [ ] Monitoreo/logs listos
- [ ] Rollback confirmado

## Rollback cookbook
- Revert seguro: `git revert <commit>`
- Reset + force: solo emergencia y con rulesets claros

## Inventario actual de workflows
- `.github/workflows/ci.yml`
  - Trigger: `push`, `pull_request`
  - Acciones: tests + smoke + kernel guard en PR
- `.github/workflows/link-check.yml`
  - Trigger: `push`, `pull_request`, `workflow_dispatch`
  - Accion: `lycheeverse/lychee-action@v1`
- `.github/workflows/repo_maintenance_bot.yml`
  - Trigger: `workflow_dispatch`
  - Requiere secretos `GH_APP_ID` y `GH_APP_PRIVATE_KEY`
  - Si faltan, salta limpio sin fallar

## Regla de cambio
Cualquier cambio en `.github/workflows` se documenta en `docs/context/STATUS.md`.
