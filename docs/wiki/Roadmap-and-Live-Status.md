# Roadmap y estado live

> **Corte de estado:** 2026-08-02.
> **Base auditada:** [`c399c94`](https://github.com/Voxterrae/HUB_Optimus/commit/c399c94e098058a723482001811c7d8491ebbd5e).
> Los Issues, PRs, Checks y Actions vivos prevalecen sobre esta página.

| Área | Estado observado | Siguiente decisión |
| --- | --- | --- |
| Web pública | Desplegada en GitHub Pages. | Mantener sincronización desde `main`. |
| Operator con texto | `c399c94` desplegado: texto completo local y URL opcional no verificada. | Completar QA real de caché y dispositivos. |
| Importación automática de URL | No operativa públicamente. | Completar backend privado autenticado. |
| Backend EC2 local | Última auditoría: host local-only pero obsoleto; estado actual no reatestado. | Adoptar el estado legado con #1832 y después acreditar SHA mediante #1831. |
| OIDC propietario/equipo | PR #1844 en borrador. | Configurar Entra, Redis, TLS y pruebas E2E. |
| QA iOS/Safari | Gate pendiente para el Operator privado. | Probar 320–1363 px, 200 %, RTL, movimiento reducido y WebGL. |
| Historial persistente | No verificado como implementado. | Diseñar después del Operator privado. |
| GitHub App Observe | Futuro. | Mantener inicialmente solo lectura. |
| Señales y grafo | Futuro. | Definir contratos y procedencia primero. |
| Consola espacial | Futuro. | Abordar después de persistencia y grafo. |

## Secuencia recomendada

1. [#1832: despliegue recuperable](https://github.com/Voxterrae/HUB_Optimus/issues/1832).
2. [#1831: desplegar y acreditar SHA](https://github.com/Voxterrae/HUB_Optimus/issues/1831).
3. [#1835: frontera pública segura](https://github.com/Voxterrae/HUB_Optimus/issues/1835).
4. [PR #1844: OIDC propietario/equipo](https://github.com/Voxterrae/HUB_Optimus/pull/1844).
5. QA real, evidencia y rollback.
6. Historial persistente → Observe → señales/grafo → consola espacial.

## Estado vivo

- [Issues](https://github.com/Voxterrae/HUB_Optimus/issues)
- [Pull requests](https://github.com/Voxterrae/HUB_Optimus/pulls)
- [Actions](https://github.com/Voxterrae/HUB_Optimus/actions)
- [Estado de capacidades versionado](https://github.com/Voxterrae/HUB_Optimus/blob/c399c94e098058a723482001811c7d8491ebbd5e/docs/architecture/capability_status.md)
