# Primer piloto público: preparar una revisión con Operator

Related to #2187. Primer piloto aprobado el 14-11-2026; aceptación visual y producción se registran por separado.

**Resultado buscado:** convertir dos declaraciones de prueba en un borrador editable con extractos, procedencia y límites visibles; copiar su JSON y comprobar cómo se elimina el trabajo local.

Estado a 14-11-2026: recorrido comprobado con JavaScript real de la página y DOM simulado sobre el commit `eb1f6b28ccba503b6c8402548a2f096e9c284e68`. La comprobación visible en navegador y la coincidencia con la versión publicada siguen pendientes. Este piloto no cambia el producto ni activa servicios privados.

## Qué puedes probar

El [Operator público](https://huboptimus.dev/operator/?lang=es) prepara un borrador en el navegador a partir de texto pegado. La URL opcional se conserva como atribución aportada y no recuperada. Una URL sola no completa este recorrido.

El resultado permite revisar qué afirma el material, separar afirmaciones y conservar los extractos exactos. `triage` significa que hace falta revisión humana. No demuestra que las declaraciones sean verdaderas ni identifica automáticamente la contradicción entre ellas. No infiere motivos, no puntúa riesgo ni ejecuta el Semantic Engine.

No hace falta una cuenta privada ni un proveedor adicional para este recorrido público. No se ha medido el coste del alojamiento o de conectividad existente; no se propone gasto recurrente nuevo.

## Material de prueba

Utiliza únicamente este ejemplo inventado, sin datos de personas ni enlaces privados.

**URL de la fuente:** `https://example.invalid/piloto-operator`

**Texto de la fuente:**

```text
El registro sintético indica dos cajas.
El recuento sintético indica tres cajas.
```

Mantén **Tipo de fuente** en la opción inicial **detectar de forma conservadora desde la URL**. La clasificación es una etiqueta de entrada y no una comprobación de la fuente.

## Recorrido y resultado observable

| Paso | Acción exacta en la interfaz ES | Qué debe observarse |
| --- | --- | --- |
| 1. Entrada | Abre Operator con `?lang=es`. Rellena **URL de la fuente** y **Texto de la fuente** con el material anterior. Pulsa **Preparar borrador**. | Se abre **Revisa la instantánea de la fuente y elige pasajes**. El texto completo sigue visible. Todavía no hay un borrador terminado. |
| 2. Pasajes | Revisa **Pasajes exactos seleccionados para este borrador**. Conserva los dos pasajes propuestos y su separador tal como aparecen. Marca **He revisado la instantánea y confirmo únicamente los pasajes exactos anteriores para este borrador. Esto confirma la selección, no la verdad ni la completitud.** | Aparece **Separar las afirmaciones de la fuente**, con dos extractos y una afirmación por extracto. La propuesta inicial es mecánica, no una selección por relevancia. |
| 3. Afirmaciones | En cada uno de los dos extractos pulsa **Marcar propuesta como revisada**. Marca **He clasificado cada propuesta como revisada u omitida y he revisado estas afirmaciones conservadas como proposiciones separadas. Registran lo que afirma la fuente; no confirman que sea verdad.** | Las dos propuestas constan como revisadas y el conjunto queda confirmado. Estas confirmaciones registran una decisión del operador sobre selección y redacción. |
| 4. Borrador | Pulsa **Preparar borrador vinculado a la fuente**. | Aparece **Borrador listo. Requiere revisión humana; no se ha ejecutado ningún Semantic Engine.** El resultado contiene dos afirmaciones y dos extractos, con señal `triage` y límites de corroboración. |
| 5. Edición | En **Separar las afirmaciones de la fuente**, cambia la primera afirmación por `El registro de prueba declara que hay dos cajas.` | La primera afirmación pasa a **Paráfrasis redactada por una persona**. El extracto original sigue diciendo `El registro sintético indica dos cajas.`. Se retira la confirmación del conjunto y se desactiva **Copiar resumen para compartir** hasta preparar un borrador vigente. |
| 6. Nueva revisión | Pulsa **Marcar propuesta como revisada** en la primera afirmación editada. Vuelve a marcar la confirmación de afirmaciones y pulsa **Preparar borrador de nuevo**. | El borrador vuelve a estar listo; conserva la paráfrasis y el extracto original como registros distintos. |
| 7. Copia del JSON | Pulsa **Avanzado · vista técnica**. En **JSON generado del caso**, pulsa **Generar JSON** y después **Copiar JSON**. Pega el contenido en un editor de texto si quieres conservar un archivo `.json`. | Se confirma **JSON del caso copiado.** La copia contiene el caso actual. Este flujo copia al portapapeles; no descarga automáticamente un archivo del borrador. Si el navegador deniega el portapapeles, la interfaz informa de que no pudo copiarlo. |
| 8. Guardado local opcional | En la misma sección pulsa **Guardar borrador localmente**. | Se informa de que el caso queda en este perfil del navegador hasta eliminarlo o sustituirlo. Guardar es una acción explícita; preparar el borrador no lo guarda automáticamente. |
| 9. Limpiar lo actual | Pulsa **Limpiar campos actuales** y acepta la confirmación que distingue campos actuales de borrador guardado. | La URL, el texto y los registros actuales se vacían; compartir queda desactivado. El borrador guardado por separado sigue existiendo. |
| 10. Comprobar y borrar lo guardado | Si realizaste el paso 8, pulsa **Cargar borrador guardado**. Comprueba que vuelven los registros y que la entrada principal se restablece para evitar mezclar procedencias. Pulsa **Eliminar borrador guardado** y acepta su confirmación. | Aparece **El borrador guardado se eliminó de este perfil del navegador.** Esta acción elimina el guardado, pero conserva los campos actuales ya cargados. Pulsa de nuevo **Limpiar campos actuales** y acepta para terminar con ambos estados vacíos. |

Los textos de los botones se toman del catálogo ES efectivo del código. El navegador y la traducción pueden necesitar revisión visual; los selectores técnicos de aceptación se incluyen al final.

## Qué contiene realmente la copia JSON

La copia del caso tiene estas claves raíz: `case_id`, `core_version_ref`, `input_summary`, `claims`, `evidence`, `inferences`, `uncertainties`, `narrative_amplification`, `operational_signal` y `metadata`. En este recorrido `case_id` se genera en cada preparación. El JSON copiado del caso no incluye `status` en la raíz; no debe confundirse con la envoltura del visor de resultados ni con el archivo de un candidato de revisión.

| Campo o ruta | Valor observado en este ejemplo | Lectura correcta |
| --- | --- | --- |
| `operational_signal` | `triage` | Revisión humana pendiente; no es una puntuación de riesgo. |
| `metadata.normalizer_version` | `operator-source-bound-v2` | Identifica el normalizador y el registro de revisión usado. |
| `metadata.semantic_engine_executed` | `false` | No hubo ejecución del Semantic Engine. |
| `metadata.verification_performed` | `false` | No se verificó la verdad del material. |
| `metadata.model_used` | `false` | Este recorrido no utilizó un modelo. |
| `metadata.intake_record.mode` | `operator-pasted-text-with-url` | La fuente de trabajo fue el texto pegado. |
| `metadata.intake_record.original_url` | `https://example.invalid/piloto-operator` | Atribución aportada por quien usa la interfaz. |
| `metadata.intake_record.attribution` | `operator-provided-url-not-fetched` | La URL no fue recuperada. |
| `metadata.intake_record.final_url`, `retrieved_at`, `bytes_read` | `null` | No hay recibo de recuperación. |
| `claims[0].metadata.source_quote_type` después de editar | `paraphrase` | La redacción editada no se presenta como cita exacta. |
| `evidence[0].text` después de editar | `El registro sintético indica dos cajas.` | El extracto exacto se conserva por separado. |
| `claims[*].metadata.support_scope` y `evidence[*].metadata.support_scope` | `attribution-only` | El vínculo respalda la atribución al material, no su verdad. |
| `metadata.relationships[*].type` | `SUPPORTS_ATTRIBUTION` | Relación candidata de atribución entre extracto y afirmación. |
| `metadata.source_text_fingerprint` y hashes de `metadata.claim_drafting` | SHA-256 del texto, selección y registros | Permiten comprobar consistencia de esta estructura; no certifican autoría ni veracidad externas. |

El guardado local utiliza una envoltura diferente: `version: operator-local-draft-v2`, `saved_at_utc` y `payload` con el caso. El espacio **Revisión estructurada del resultado** tiene su propio flujo de candidatos y su propia descarga JSON; no es necesario para aceptar este primer piloto.

## Alcance comprobado y límites

Las pruebas existentes relevantes pasaron: **116 passed in 30.48s** (`test_operator_pwa_product_actions`, `test_operator_pwa_record_integrity`, `test_operator_claim_decomposition`, `test_operator_primary_i18n` y `test_operator_private_session_boundary`).

La ejecución automática de este ejemplo usó el script completo de Operator, el catálogo ES y el módulo de descomposición del repositorio dentro de su harness Node con DOM simulado. Se accionaron los manejadores registrados de envío, confirmación, revisión, edición, copia, guardado, carga y borrado. Los destinos dinámicos delegados se representaron con los selectores reales. Para estructuras JSON se adaptó el clonado al contexto VM, evitando una diferencia de prototipos del harness; no se cambió código del producto.

Se obtuvo: dos afirmaciones y dos extractos; `triage`; edición marcada como paráfrasis; invalidación de la versión compartible tras editar; copia idéntica al JSON mostrado; conservación del guardado al limpiar lo actual; carga sin reatribuir la entrada principal; eliminación del guardado; limpieza final con cero registros. Se registraron **cero llamadas a `fetch` en este recorrido de entrada**. Esta observación no significa que cargar los archivos de la página carezca de tráfico de red.

Esta evidencia no acredita renderizado real, accesibilidad con lector de pantalla, permiso real del portapapeles, confirmaciones nativas, persistencia entre sesiones o coincidencia de los bytes publicados. El borrado local tampoco retira copias ya pegadas, descargas, historial externo o copias realizadas por otras aplicaciones, ni constituye borrado forense. No se ofrece garantía de cifrado del almacenamiento local.

## Aceptación visible pendiente

Una persona debe repetir los pasos 1–10 en la versión pública y registrar fecha, versión servida, resultado de cada paso y cualquier diferencia. Comprobar en escritorio y móvil que puede leer ambos extractos, editar sin perder el foco, operar con teclado y distinguir el borrado actual del guardado. Verificar el permiso del portapapeles y la persistencia real tras recargar únicamente si se guardó de forma explícita. No debe presentarse este recorrido como aceptado visualmente antes de observar esas comprobaciones.

La aceptación de este piloto demuestra una utilidad pública acotada: preparar y transportar material de revisión con procedencia y límites. La activación de recuperación privada de URL, cualquier análisis de backend o ejecución operativa requieren evidencias y aceptación separadas.

## Selectores para comprobar el recorrido

| Control o lectura | Selector |
| --- | --- |
| URL y texto de entrada | `#product_source_url`, `#product_source_text` |
| Tipo de fuente | `#signal_source_type` |
| Preparar / volver a preparar | `#product_analyze` |
| Instantánea y selección | `#product_source_preview_text`, `#product_source_selection` |
| Confirmación de pasajes | `#product_confirm_source` |
| Afirmaciones de este fixture | `#product_claim_0_0`, `#product_claim_1_0` |
| Revisar propuesta, por extracto | `[data-claim-group="0"] [data-review-claim-proposal="0"]`, `[data-claim-group="1"] [data-review-claim-proposal="0"]` |
| Confirmación de afirmaciones | `#product_confirm_claims` |
| Estado y resultado | `#product_wait_status`, `#product_output` |
| Compartir habilitado/deshabilitado | `#share_memory_link` |
| Abrir vista avanzada | `#product_show_advanced`, `#advanced_operator_console` |
| JSON y copia | `#build_json`, `#case_json`, `#copy_json` |
| Guardar, cargar y eliminar el guardado | `#save_draft`, `#load_draft`, `#delete_saved_draft` |
| Limpiar lo actual | `#clear_all` |

Fuente del comportamiento: `site/operator/index.html`, `site/operator/i18n.v1.js` y `site/operator/claim-decomposition.v1.js` en el commit indicado. No se modificaron interfaz, runtime, conectores, AWS, credenciales ni publicación para preparar esta propuesta.
