# WORKFLOWS — Merge / Deploy / Automatización

## Qué es “automatización” aquí (en humano)
Define qué proceso se dispara: tests, build, lint, generación de docs, releases, etc.

## Checklist PRE-MERGE
- [ ] Pull de main actualizado
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
