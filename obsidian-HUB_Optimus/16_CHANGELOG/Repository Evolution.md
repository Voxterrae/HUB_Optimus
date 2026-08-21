---
type: "changelog"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "history"
  - "changelog"
  - "architecture"
---

# Repository Evolution

> Selected architecture-relevant commits, not a complete changelog.

| Date | Commit | Change | Architectural effect |
| --- | --- | --- | --- |
| `2026-08-16` | [`30e985226347`](https://github.com/Voxterrae/HUB_Optimus/commit/30e985226347b4bc59b0e187b96633a09647ca42) | Ratificación de autoridad fundador-propietario (#1861). | Actualiza la frontera de autoridad y el baseline actual. |
| `2026-08-03` | [`ab62e8ed079f`](https://github.com/Voxterrae/HUB_Optimus/commit/ab62e8ed079f677c91a864475fe3665e634cf1f6) | Despliegue EC2 recuperable (#1847). | Añade preflight, atestación, rollback transaccional y adopción legacy. |
| `2026-08-02` | [`c399c94e0980`](https://github.com/Voxterrae/HUB_Optimus/commit/c399c94e098058a723482001811c7d8491ebbd5e) | Mantener intake público del Operator local (#1846). | Evita afirmar un backend público disponible. |
| `2026-08-02` | [`8426b08e5f88`](https://github.com/Voxterrae/HUB_Optimus/commit/8426b08e5f88b650c4d79e41d3ce3afd7d42746b) | Landing responsive y task-first (#1833). | Establece patrones visuales y de accesibilidad reutilizados. |
| `2026-08-02` | [`b5747aebfc06`](https://github.com/Voxterrae/HUB_Optimus/commit/b5747aebfc065f84103c9a6fad59a277fc28c0b8) | Operator multilingüe y review loop (#1834). | Amplía la interfaz local y su frontera humana. |
| `2026-08-02` | [`d8501c9f7165`](https://github.com/Voxterrae/HUB_Optimus/commit/d8501c9f71656afc1c11542702f568aab41818cf) | Learning candidate/store local (#1836). | Añade persistencia IndexedDB local, versionada y no canónica. |
| `2026-07-29` | [`d255dd254466`](https://github.com/Voxterrae/HUB_Optimus/commit/d255dd2544663752db282a875c77bfaedef24868) | Mapa de arquitectura actual (#1821). | Separa sistema, runtime, metodología, documentación, datos y gobierno. |
| `2026-07-29` | [`01b6ba232607`](https://github.com/Voxterrae/HUB_Optimus/commit/01b6ba232607d7d65675d4b35406f81555b23226) | Contrato canónico de controlled intake (#1811). | Fija payloads, límites y errores del endpoint. |

## Reading the History

- Recent commits strengthen provenance, local-first behavior and truthful public boundaries.
- Architecture documentation from 2026-07-29 predates later Operator, deployment and governance changes.
- Current behavior must be read from the current tree, not from a selected historical commit alone.

## Related

- [[Decision Record Map]]
- [[Evidence Index]]
- [[Repository Analysis]]
