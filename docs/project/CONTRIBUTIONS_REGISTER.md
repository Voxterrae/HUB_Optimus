# Portfolio y registro público de contribuciones

Related to #2185. Refs #1936; ambas incidencias permanecen abiertas.

Comprobación: **14 de noviembre de 2026 (Europe/Madrid)**. Registro público
estático preparado con ayuda de Codex para revisión humana. No implanta la
aplicación Contribution Ledger ni acredita su ratificación.

## Qué cubre

- **417 commits** alcanzables desde el primer commit del repositorio,
  [12-12-2025](https://github.com/Voxterrae/HUB_Optimus/commit/c7dd0f6da3a97fe52ad2ce025f87842d4ca6e9ac), hasta
  [bba055a (11-11-2026)](https://github.com/Voxterrae/HUB_Optimus/commit/bba055a72a9bed6b3d46158007bc887706f675f5).
  El [índice completo](../../site/data/repository-history.v1.json) conserva SHA y
  fecha; cada SHA tiene URL bajo `https://github.com/Voxterrae/HUB_Optimus/commit/`.
- **17 entradas del catálogo existente**, con su madurez; 15 tienen fuente o
  documentación integrada y 2 son propuestas de issue. Los 14 soportes agrupados,
  el archivo histórico y los 16 RFC Draft se listan aparte y no suman productos.
- **Tres aportaciones externas verificadas**, distinguiendo su aportación propia
  del parche upstream, su aceptación y su publicación.

El grafo de commits está indexado hasta ese corte. Esto no demuestra lectura de
todos los blobs históricos, ni cubre todas las conversaciones, PR sin integrar,
revisiones, ramas, forks o trabajo privado. El clon no es superficial y utiliza
objetos bajo demanda. La primera fecha Git no certifica un origen anterior del
proyecto ni autoría intelectual exclusiva.

Los datos consultables están en [contributions.v1.json](../../site/data/contributions.v1.json).
El [catálogo](../../products/README.md) y el [registry de capacidades](../../site/data/capability-registry.v1.json)
conservan su revisión de 08-11-2026. Los primeros/últimos commits por ruta de este
registro son evidencia histórica, no una nueva certificación de capacidades.

## Aportaciones a otros proyectos

| Fecha de publicación (Madrid) | Aportación propia | Estado observado / límite |
| --- | --- | --- |
| 11-11-2026 15:54 | [actions/setup-dotnet PR #804](https://github.com/actions/setup-dotnet/pull/804): documentación para regenerar ambos bundles tras actualizar dependencias | Abierta, sin integrar; HEAD `6c5068192fb1bf42b866e48ebfa6493c1d262f01`. No es un parche de runtime. |
| 14-11-2026 16:35 | [AWS CDK Discussion #39733](https://github.com/aws/aws-cdk/discussions/39733): validación del artefacto publicado y seguimiento de release | Publicada, sin respuesta observada; no acredita remediación de HUB_Optimus. El parche original [#39595](https://github.com/aws/aws-cdk/pull/39595) es de **udondan**, merge `c153af906a24dde1797fbd15153ca2c4b29317d5`. |
| 14-11-2026 16:45 | [Smithy PR #2351, comentario de validación](https://github.com/smithy-lang/smithy-typescript/pull/2351#issuecomment-6880003584): comparación de helpers y seguimiento de publicación | Publicado, sin respuesta a nuestra aportación observada. El parche original [#2351](https://github.com/smithy-lang/smithy-typescript/pull/2351) es de **Alan4506**, merge `c364c4863d5429f3a019a5fc020cbd57cf4ebf17`; no se atribuye a Voxterrae. |

Los tres objetos identifican a `Voxterrae` (ID público `249308740`) y declaran
asistencia de Codex. La validación Smithy comunicada cubre lógica aislada de dos
helpers (1.562 comprobaciones por implementación), no compilación completa,
compatibilidad del paquete ni integración en HUB_Optimus. La discusión CDK
comprueba el artefacto, no convierte la versión publicada en una corrección.
La aceptación del aporte propio por los mantenedores no está confirmada.

## Creaciones del catálogo

Cada ficha se enlaza a fuente pública fija. Dos fichas solo issue siguen siendo
propuestas. Ver el catálogo para las fronteras de ejecución y el crédito de los
contribuidores en los commits/PR originales.

| Creación | Madurez documentada | Primera / última fuente por ruta | Evidencia al corte |
| --- | --- | --- | --- |
| HUB_Optimus Core | active-methodology | [2025-12-25 · 91d1604](https://github.com/Voxterrae/HUB_Optimus/commit/91d160430241437cf16c17ff83289acbdcc46c93) / [2026-07-23 · 62fdb43](https://github.com/Voxterrae/HUB_Optimus/commit/62fdb439759217d2ff2ef727e99fd18d96e61c37) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/v1_core) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/context/STATUS.md) |
| Deterministic Scenario Simulator | working-deterministic-prototype | [2026-01-30 · 18f7d16](https://github.com/Voxterrae/HUB_Optimus/commit/18f7d1625ac69572bc3a85aa7362f3961b70ad7f) / [2026-09-30 · 03ee638](https://github.com/Voxterrae/HUB_Optimus/commit/03ee6387a9a69f615bba077c87150999bf054e41) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/hub_optimus_simulator.py) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/run_scenario.py) |
| Semantic Engine Contracts and CLI | early-implementation | [2026-05-30 · 907a166](https://github.com/Voxterrae/HUB_Optimus/commit/907a1668d814a8b8fd68869b0d64ac6417073dbd) / [2026-07-29 · 824d560](https://github.com/Voxterrae/HUB_Optimus/commit/824d5602e11f3e0eea84baed1cc085c613dc7e59) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/semantic_engine) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/architecture/semantic_engine_cli.md) |
| HUB_Optimus Operator | browser-prototype | [2026-06-30 · b19a316](https://github.com/Voxterrae/HUB_Optimus/commit/b19a316cbd4603541bbd4829446987e08a9ce2ba) / [2026-11-08 · 3426dbb](https://github.com/Voxterrae/HUB_Optimus/commit/3426dbbc5cd59cdb8ff6a6b91edc404dd31ea95a) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/site/operator) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/operator_atomic_claim_drafting.md) |
| Controlled URL Intake | implementation-present-deployment-unverified | [2026-07-20 · cfe5e2c](https://github.com/Voxterrae/HUB_Optimus/commit/cfe5e2c70a4dc87961b23d11c19c64efb3a80fd0) / [2026-11-08 · e150ece](https://github.com/Voxterrae/HUB_Optimus/commit/e150eced156c22c624366a5c681ae41df9a347e1) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/operator_controlled_url_intake.md) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/ops/ec2/controlled_url_intake.v1.schema.json) |
| Scenario and Narrative Research | experimental-tooling | [2026-03-09 · 7060596](https://github.com/Voxterrae/HUB_Optimus/commit/7060596f05b449cca0cdfaccd3a3b5a441a3360a) / [2026-10-25 · 2197305](https://github.com/Voxterrae/HUB_Optimus/commit/21973051fc32823df1aa6b05b0ff7ad99bb4d21d) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/tools/scenario_generator) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/tools/scenario_mutator.py) |
| Governance Intelligence | active-ratified-protocol | [2026-07-17 · e829980](https://github.com/Voxterrae/HUB_Optimus/commit/e82998079340f63807e506f6bd7a07ce5b184eee) / [2026-07-17 · e829980](https://github.com/Voxterrae/HUB_Optimus/commit/e82998079340f63807e506f6bd7a07ce5b184eee) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/governance/GOVERNANCE_INTELLIGENCE.md) |
| HUB-Optimus Labs | documented-incubation-surface | [2026-07-28 · 581aab7](https://github.com/Voxterrae/HUB_Optimus/commit/581aab7f858ff109b06d2b7737084cb660637c7a) / [2026-11-08 · e674c09](https://github.com/Voxterrae/HUB_Optimus/commit/e674c098e2ad11b8722ba34e493be7d705f8db2d) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/site/index.html) |
| Optimus Admin Gateway | implementation-present-deployment-unverified | [2026-09-14 · ebe288e](https://github.com/Voxterrae/HUB_Optimus/commit/ebe288effbdc3307c8f9f6c509178f66fe42484f) / [2026-11-02 · ab904f9](https://github.com/Voxterrae/HUB_Optimus/commit/ab904f96f8a4848171a9764ff26f505f7451a888) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/products/admin-gateway) |
| Optimus Evidence Lab | implementation-present-deployment-unverified | [2026-09-30 · 5132728](https://github.com/Voxterrae/HUB_Optimus/commit/51327282170b9c0a6f769b8bd5ddc5c39572d6a4) / [2026-09-30 · 5132728](https://github.com/Voxterrae/HUB_Optimus/commit/51327282170b9c0a6f769b8bd5ddc5c39572d6a4) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/products/evidence-lab) |
| HUB_Optimus Connect — xAI and X Foundation | early-implementation | [2026-09-14 · bd7cfd3](https://github.com/Voxterrae/HUB_Optimus/commit/bd7cfd3cf39e36d7a9f9c215cd5d47635d63cf41) / [2026-09-14 · bd7cfd3](https://github.com/Voxterrae/HUB_Optimus/commit/bd7cfd3cf39e36d7a9f9c215cd5d47635d63cf41) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/hub_optimus/connect) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/architecture/xai_x_signal_bridge.md) |
| Optimus Global Graph | issue-only | — / — | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/issues/1880) |
| Optimus Browser — Windows | early-implementation | [2026-10-30 · 4002b84](https://github.com/Voxterrae/HUB_Optimus/commit/4002b849d0c2614627fc876b89bce8e21556d3a9) / [2026-11-08 · df1150f](https://github.com/Voxterrae/HUB_Optimus/commit/df1150fc7c60fe7606a5a4ccce5be34d518bb2a4) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/products/browser/windows) |
| Optimus Browser — Web Pilot | browser-prototype | [2026-10-30 · 5b1f598](https://github.com/Voxterrae/HUB_Optimus/commit/5b1f5989a6626ad1abe9ba84ef42595bd77f4c16) / [2026-10-30 · 5b1f598](https://github.com/Voxterrae/HUB_Optimus/commit/5b1f5989a6626ad1abe9ba84ef42595bd77f4c16) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/products/browser/web) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/site/browser) |
| Optimus Browser — Linux | issue-only | — / — | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/issues/2021) |
| Optimus Search | implementation-present-deployment-unverified | [2026-11-01 · 10512ad](https://github.com/Voxterrae/HUB_Optimus/commit/10512ad8270f274cf69797a642e2f8bb309aa878) / [2026-11-08 · 376eb0e](https://github.com/Voxterrae/HUB_Optimus/commit/376eb0eb2f288d6c4bc666e27d343082c81f07f2) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/products/browser/search) |
| Device Bridge / HUB_Relay | experimental-tooling | [2026-09-30 · e48a10b](https://github.com/Voxterrae/HUB_Optimus/commit/e48a10bfc0fbe63ca99c29ccc1279398f0a957f6) / [2026-11-08 · eec3c3f](https://github.com/Voxterrae/HUB_Optimus/commit/eec3c3f078f9b47af7ba7e37570d8087ea7714de) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/products/device-bridge) |

## Capacidades y creaciones agrupadas

No son productos adicionales ni servicios certificados en producción.
Project Intelligence / Obsidian se conserva como explorador experimental de
arquitectura y conocimiento derivado, con sus versiones históricas.

| Creación o soporte | Madurez documentada | Primera / última fuente por ruta | Evidencia al corte |
| --- | --- | --- | --- |
| Project Intelligence / Obsidian Explorer | experimental | [2026-09-14 · c7d08b7](https://github.com/Voxterrae/HUB_Optimus/commit/c7d08b78d38148ffc6f84b9f2dd8541149d224ff) / [2026-09-14 · f965ebd](https://github.com/Voxterrae/HUB_Optimus/commit/f965ebdbec6809fa6311aed76a7ae0d4fb8232e5) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/obsidian-HUB_Optimus) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/site/obsidian-HUB_Optimus) |
| Sitio público y presentación estática/PWA | browser-prototype | [2026-06-24 · 70bc1f6](https://github.com/Voxterrae/HUB_Optimus/commit/70bc1f61d0316608133b6db6ec235fd1d1b5312c) / [2026-11-08 · e674c09](https://github.com/Voxterrae/HUB_Optimus/commit/e674c098e2ad11b8722ba34e493be7d705f8db2d) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/site/index.html) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/site/assets) |
| Prototipo local ControlPlane | experimental | [2026-02-08 · 351cad7](https://github.com/Voxterrae/HUB_Optimus/commit/351cad7d40329023595d5e64045c122f64cff0a1) / [2026-07-29 · a79d3ee](https://github.com/Voxterrae/HUB_Optimus/commit/a79d3eef14fbea633814e448daf2aca859b24d5f) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/hub_optimus/hub_optimus_control.py) |
| Runner, registro de ejecuciones y API local EC2 | prototype-partial | [2026-06-27 · 2dea811](https://github.com/Voxterrae/HUB_Optimus/commit/2dea8113a8526af44d9a3ee9bc48aee44ffe2ef3) / [2026-10-25 · 2197305](https://github.com/Voxterrae/HUB_Optimus/commit/21973051fc32823df1aa6b05b0ff7ad99bb4d21d) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/ops/ec2) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/scripts/infra) |
| CLI local de entrada móvil | prototype | [2026-05-15 · 65732b9](https://github.com/Voxterrae/HUB_Optimus/commit/65732b978b93d89d9e6a70320f4d3126fab7c9dc) / [2026-07-29 · 46e890e](https://github.com/Voxterrae/HUB_Optimus/commit/46e890e2328ffaed2f1a1f384ed21b31a112feaa) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/tools/mobile_ingest.py) |
| Candidatos y almacén local de aprendizaje Operator | draft-local-workflow-implemented | [2026-08-02 · d8501c9](https://github.com/Voxterrae/HUB_Optimus/commit/d8501c9f71656afc1c11542702f568aab41818cf) / [2026-09-30 · 67e2f41](https://github.com/Voxterrae/HUB_Optimus/commit/67e2f41465790445f8ab755f01801a3915e90230) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/site/operator/learning-store.v1.js) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/site/operator/learning-candidate.v1.js) |
| Descomposición de afirmaciones atómicas confirmada por humanos | accepted-bounded-source | [2026-09-30 · 67e2f41](https://github.com/Voxterrae/HUB_Optimus/commit/67e2f41465790445f8ab755f01801a3915e90230) / [2026-09-30 · 67e2f41](https://github.com/Voxterrae/HUB_Optimus/commit/67e2f41465790445f8ab755f01801a3915e90230) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/site/operator/claim-decomposition.v1.js) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/operator_atomic_claim_drafting.md) |
| Generador y herramientas de mutación, telemetría y fronteras | experimental | [2026-03-09 · 7060596](https://github.com/Voxterrae/HUB_Optimus/commit/7060596f05b449cca0cdfaccd3a3b5a441a3360a) / [2026-10-25 · 2197305](https://github.com/Voxterrae/HUB_Optimus/commit/21973051fc32823df1aa6b05b0ff7ad99bb4d21d) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/tools/scenario_generator) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/tools/scenario_mutator.py) |
| Corpus narrativos y comprobaciones de consistencia | implemented-structural-checks-provisional-content | [2026-03-22 · 661c3d7](https://github.com/Voxterrae/HUB_Optimus/commit/661c3d7ecf040fa0fb2ca9a5efbf8f902b72df76) / [2026-07-29 · 8701b08](https://github.com/Voxterrae/HUB_Optimus/commit/8701b083d24fbea52d9faa0207ab51010ba61273) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/datasets) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/benchmarks/run_narrative_benchmarks.py) |
| Normas de gobernanza y herramientas del repositorio | active-documents-and-bounded-implemented-tools | [2026-01-05 · 27b59cc](https://github.com/Voxterrae/HUB_Optimus/commit/27b59ccafdbeafc39e1f3d9050c8c6ed17cdd0ed) / [2026-10-03 · 1c4a61b](https://github.com/Voxterrae/HUB_Optimus/commit/1c4a61be49dbcc4dbb5344da139b561f4a76a207) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/docs/governance) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/tools/kernel_guard.py) |
| Demo adaptable React de Optimus | interface-demo | [2026-10-30 · 4002b84](https://github.com/Voxterrae/HUB_Optimus/commit/4002b849d0c2614627fc876b89bce8e21556d3a9) / [2026-10-30 · 4002b84](https://github.com/Voxterrae/HUB_Optimus/commit/4002b849d0c2614627fc876b89bce8e21556d3a9) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/products/browser/demo) |
| API remota de catálogo piloto | inactive-implementation-deployment-unverified | [2026-11-08 · 18c2004](https://github.com/Voxterrae/HUB_Optimus/commit/18c20047ba66e7478e76fcba49014553f713427b) / [2026-11-08 · 18c2004](https://github.com/Voxterrae/HUB_Optimus/commit/18c20047ba66e7478e76fcba49014553f713427b) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/products/browser/search/remote) |
| Adaptador Brave y gateway web autenticado | inactive-local-candidate | [2026-11-08 · 6eebd71](https://github.com/Voxterrae/HUB_Optimus/commit/6eebd712c116932e3a6b9d397709f1140220b786) / [2026-11-08 · 376eb0e](https://github.com/Voxterrae/HUB_Optimus/commit/376eb0eb2f288d6c4bc666e27d343082c81f07f2) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/products/browser/search/providers/brave) |
| Canary privado AWS para una URL | disabled-repository-candidate | [2026-09-30 · 2359fb9](https://github.com/Voxterrae/HUB_Optimus/commit/2359fb9dd3d0cdb8150fc6c60c622c3e8e558b4a) / [2026-11-08 · e150ece](https://github.com/Voxterrae/HUB_Optimus/commit/e150eced156c22c624366a5c681ae41df9a347e1) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/ops/aws/operator-url-intake) |

El adaptador/gateway Brave y la API remota tienen fuente integrada después de
parte de la revisión del catálogo; permanecen inactivos o candidatos y no se
presentan como despliegues. No se han leído ni publicado diagnósticos privados.

## Archivo y propuestas

En la fila del archivo v0, la primera fecha corresponde al paquete público original
del 12-12-2025, no al traslado posterior a legacy. El JSON conserva por separado
paquete inicial, documentos individuales, separación del archivo y último cambio.
El archivo v0 preserva material exploratorio no canónico. Los RFC Draft son
propuestas documentales; la integración del texto no demuestra implementación.

| Archivo o propuesta | Madurez | Primera / última fuente por ruta | Evidencia al corte |
| --- | --- | --- | --- |
| Archivo exploratorio v0: paz, diplomacia y participación cívica | historical / legacy / non-canonical | [2025-12-12 · 2bb8851](https://github.com/Voxterrae/HUB_Optimus/commit/2bb8851c66586a48a0be3e8d1a8ed2c41a7a019b) / [2026-07-29 · 55a1334](https://github.com/Voxterrae/HUB_Optimus/commit/55a13347f8373a409adbb0a08019de2d85a57873) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/tree/bba055a72a9bed6b3d46158007bc887706f675f5/legacy/v0_exploratory) · [fuente 2](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/legacy/v0_exploratory/HISTORICAL_RELEASE_2025-12-12.md) |
| AI / LLM Provider Independence | Draft | [2026-06-14 · 70b55fd](https://github.com/Voxterrae/HUB_Optimus/commit/70b55fd45b28c7c5e3593253e97eb104dfa38ab2) / [2026-06-14 · 70b55fd](https://github.com/Voxterrae/HUB_Optimus/commit/70b55fd45b28c7c5e3593253e97eb104dfa38ab2) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/ai_llm_provider_independence.md) |
| Constitutional Governance and AI Regulatory Boundary | Draft | [2026-06-09 · da95c33](https://github.com/Voxterrae/HUB_Optimus/commit/da95c3303124adf7b54e337b86c6ca8010f75a59) / [2026-06-09 · da95c33](https://github.com/Voxterrae/HUB_Optimus/commit/da95c3303124adf7b54e337b86c6ca8010f75a59) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/constitutional_governance_ai_regulatory_boundary.md) |
| Enterprise Boundary | Draft | [2026-06-14 · 6bebdfe](https://github.com/Voxterrae/HUB_Optimus/commit/6bebdfe2b65062c984f91d7bcf987b2933e05c81) / [2026-07-28 · 1eb1236](https://github.com/Voxterrae/HUB_Optimus/commit/1eb1236bc4d0861ec9e33358e90dfe7ea7ae2572) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/enterprise_boundary.md) |
| Epistemic Analysis Modes | Draft | [2026-06-10 · 1895a7f](https://github.com/Voxterrae/HUB_Optimus/commit/1895a7f167acaa5137fc7c9f7720a9fe90760f3a) / [2026-06-10 · 1895a7f](https://github.com/Voxterrae/HUB_Optimus/commit/1895a7f167acaa5137fc7c9f7720a9fe90760f3a) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/epistemic_analysis_modes.md) |
| GitHub Platform Strategy for HUB_Optimus Evolution | Draft | [2026-07-09 · 748716f](https://github.com/Voxterrae/HUB_Optimus/commit/748716fefe340f7e8de9920949d77b2477bb77ff) / [2026-07-09 · 748716f](https://github.com/Voxterrae/HUB_Optimus/commit/748716fefe340f7e8de9920949d77b2477bb77ff) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/github_platform_strategy.md) |
| HUB_Optimus Evidence Bridge | Draft | [2026-09-14 · f4c916a](https://github.com/Voxterrae/HUB_Optimus/commit/f4c916ad29e17d96957cff8c6d12cac954bc420e) / [2026-09-14 · f4c916a](https://github.com/Voxterrae/HUB_Optimus/commit/f4c916ad29e17d96957cff8c6d12cac954bc420e) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/hub_optimus_evidence_bridge.md) |
| HERMES PWA Gate Issue Pack | Draft | [2026-06-30 · ff975f5](https://github.com/Voxterrae/HUB_Optimus/commit/ff975f5b55c550ca4a481060cf34730c91c27cbe) / [2026-06-30 · ff975f5](https://github.com/Voxterrae/HUB_Optimus/commit/ff975f5b55c550ca4a481060cf34730c91c27cbe) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/hermes_pwa_gate_issue_pack.md) |
| HERMES PWA Interface Boundary | Draft | [2026-06-14 · 70b62fd](https://github.com/Voxterrae/HUB_Optimus/commit/70b62fd7d6e144c146569569d31e13a97702586b) / [2026-06-30 · ff975f5](https://github.com/Voxterrae/HUB_Optimus/commit/ff975f5b55c550ca4a481060cf34730c91c27cbe) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/hermes_pwa_interface_boundary.md) |
| Ingestion and Evidence Intake Boundary | Draft | [2026-06-14 · 855fd68](https://github.com/Voxterrae/HUB_Optimus/commit/855fd6853eec6e78928e4e5a01882088d417c28b) / [2026-06-14 · 855fd68](https://github.com/Voxterrae/HUB_Optimus/commit/855fd6853eec6e78928e4e5a01882088d417c28b) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/ingestion_evidence_intake_boundary.md) |
| IEG — Intelligent Ecosystem Guardian | Draft | [2026-07-16 · 619e622](https://github.com/Voxterrae/HUB_Optimus/commit/619e6223323d05f0fd3856fc327e28e0fe38a2d8) / [2026-07-16 · 619e622](https://github.com/Voxterrae/HUB_Optimus/commit/619e6223323d05f0fd3856fc327e28e0fe38a2d8) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/intelligent_ecosystem_guardian.md) |
| IP / Patent / Confidential Disclosure Boundary | Draft | [2026-06-14 · 866442e](https://github.com/Voxterrae/HUB_Optimus/commit/866442ea6d9bcb8bec4784af1d546f7dcea3b598) / [2026-06-14 · 866442e](https://github.com/Voxterrae/HUB_Optimus/commit/866442ea6d9bcb8bec4784af1d546f7dcea3b598) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/ip_confidential_disclosure_boundary.md) |
| Judicial Transparency Audit Framework | Draft | [2026-06-19 · f57fff6](https://github.com/Voxterrae/HUB_Optimus/commit/f57fff6d031dd9b767b342ce40d44eb5fcf4a3ee) / [2026-06-20 · 00b6a1a](https://github.com/Voxterrae/HUB_Optimus/commit/00b6a1ad32d677e12e621c154d68c3705e55499b) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/judicial_transparency_audit_framework.md) |
| Post-Quantum Control Plane | Draft | [2026-05-24 · b76cb8d](https://github.com/Voxterrae/HUB_Optimus/commit/b76cb8dbed756b01ef0bb9a4473c32e24014a75d) / [2026-05-24 · b76cb8d](https://github.com/Voxterrae/HUB_Optimus/commit/b76cb8dbed756b01ef0bb9a4473c32e24014a75d) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/post_quantum_control_plane.md) |
| Proposal and Scenario Analysis Mode | Draft | [2026-06-06 · c1728ea](https://github.com/Voxterrae/HUB_Optimus/commit/c1728ea23391b4fefe805e47fa133c279ef10569) / [2026-06-06 · c1728ea](https://github.com/Voxterrae/HUB_Optimus/commit/c1728ea23391b4fefe805e47fa133c279ef10569) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/proposal_scenario_analysis_mode.md) |
| WhatsApp Claim Intake Adapter Boundary | Draft | [2026-06-30 · 4fa7a10](https://github.com/Voxterrae/HUB_Optimus/commit/4fa7a10979fe6bef734356792f1594f6131d1727) / [2026-06-30 · 4fa7a10](https://github.com/Voxterrae/HUB_Optimus/commit/4fa7a10979fe6bef734356792f1594f6131d1727) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/whatsapp_claim_intake_adapter_boundary.md) |
| AI Access Matrix | Draft | [2026-10-25 · 7f6473e](https://github.com/Voxterrae/HUB_Optimus/commit/7f6473e0e2607e581e686e3fe5b56cf43bfa958f) / [2026-10-25 · 7f6473e](https://github.com/Voxterrae/HUB_Optimus/commit/7f6473e0e2607e581e686e3fe5b56cf43bfa958f) | [fuente 1](https://github.com/Voxterrae/HUB_Optimus/blob/bba055a72a9bed6b3d46158007bc887706f675f5/docs/rfc/ai_access_matrix.md) |

## Cobertura pendiente y mantenimiento

Las búsquedas públicas desde la creación de la cuenta (12-12-2025) incluyeron
PR/issues por autor, revisiones/commenter/involves, Discussions y eventos
paginados. **La cobertura externa sigue siendo parcial**: el comentario Smithy
existe en lectura directa y no aparece en la búsqueda commenter. El feed de
eventos tiene retención limitada y páginas solapadas. No convertir resultados
vacíos en ausencia de aportaciones.

Pendiente: reconciliar conversaciones internas y PR no integradas desde el
inicio; recuperar aportes externos omitidos por el índice; documentar creaciones
fuera de este repositorio mediante fichas públicas saneadas. Las superficies de
acceso restringido quedan sin enlaces ni nombres privados en este registro.
No se verifica ninguna aportación externa adicional a partir de recuerdos.

Para actualizar: leer el objeto público y sus comentarios/revisiones; registrar
URL, contribuidor, tipo de aportación, fecha y observación; separar envío,
aceptación, merge, paquete publicado y validación en HUB_Optimus. Actualizar el
índice Git con un corte explícito y revisar la cobertura antes de cambiar los
recuentos. Corregir registros sin borrar el rastro de versiones Git. Toda
ampliación pasa por PR revisada; no hay sincronización ni publicación automática.

El registro no sustituye los commits/PR originales ni establece autoría humana
exclusiva. Debe conservar crédito real, asistencia de IA, derechos y licencias
de terceros conforme a los documentos de autoridad vigentes. No publicar datos
de clientes, secretos, correos, costes, expedientes ni pruebas privadas. Ningún
enlace o resultado implica patrocinio por GitHub, AWS, Smithy o Microsoft.
