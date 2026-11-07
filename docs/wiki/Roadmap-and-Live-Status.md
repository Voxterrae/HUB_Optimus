# Roadmap y estado live

> **Revisión documental:** 2026-10-16; no reatesta despliegues ni servicios externos.
> **Base documental:** [`23ea5a6`](https://github.com/Voxterrae/HUB_Optimus/commit/23ea5a6677c07dcefab60f70c6b1641a3541f0b0).
> Los Issues, PRs, Checks y Actions vivos prevalecen sobre esta página.

| Área | Estado observado | Siguiente decisión |
| --- | --- | --- |
| Web pública | Auditoría histórica: desplegada en GitHub Pages; estado actual no reatestado. | Mantener sincronización desde `main`. |
| Operator con texto | Última auditoría pública en `c399c94`: texto completo local y URL opcional no verificada. | Completar QA real de caché y dispositivos. |
| Importación automática de URL | No operativa públicamente. | Completar backend privado autenticado. |
| Backend EC2 local | Última auditoría: host local-only pero obsoleto; estado actual no reatestado. | Adoptar el estado legado con #1832 y después acreditar SHA mediante #1831. |
| OIDC propietario/equipo | Código integrado mediante PR #1844; despliegue no reatestado. | Configurar Entra, Redis, TLS y pruebas E2E. |
| QA iOS/Safari | Gate pendiente para el Operator privado. | Probar 320–1363 px, 200 %, RTL, movimiento reducido y WebGL. |
| Historial persistente | No verificado como implementado. | Diseñar después del Operator privado. |
| GitHub App Observe | Futuro. | Mantener inicialmente solo lectura. |
| Señales y grafo | Explorador documental versionado; no acredita señales externas activas. | Definir contratos y procedencia primero. |
| Consola espacial | Futuro. | Abordar después de persistencia y grafo. |

## Secuencia recomendada

1. [#1832: despliegue recuperable](https://github.com/Voxterrae/HUB_Optimus/issues/1832).
2. [#1831: desplegar y acreditar SHA](https://github.com/Voxterrae/HUB_Optimus/issues/1831).
3. [#1835: frontera pública segura](https://github.com/Voxterrae/HUB_Optimus/issues/1835).
4. [PR #1844: OIDC propietario/equipo](https://github.com/Voxterrae/HUB_Optimus/pull/1844).
5. QA real, evidencia y rollback.
6. Historial persistente → Observe → señales/grafo → consola espacial.

El [handoff técnico](https://github.com/Voxterrae/HUB_Optimus/blob/23ea5a6677c07dcefab60f70c6b1641a3541f0b0/docs/context/AI_HANDOFF.md)
documenta el explorador y su modelo derivado, fechado; su presencia no acredita
un despliegue actual ni transportes externos activos.

## Estado vivo

- [Issues](https://github.com/Voxterrae/HUB_Optimus/issues)
- [Pull requests](https://github.com/Voxterrae/HUB_Optimus/pulls)
- [Actions](https://github.com/Voxterrae/HUB_Optimus/actions)
- [Estado de capacidades versionado](https://github.com/Voxterrae/HUB_Optimus/blob/23ea5a6677c07dcefab60f70c6b1641a3541f0b0/docs/architecture/capability_status.md)
