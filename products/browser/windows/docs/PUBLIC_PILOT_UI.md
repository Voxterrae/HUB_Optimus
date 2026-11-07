# Catálogo público piloto desde Windows — issue2083

En **Tu índice** o al elegir **Índice Optimus**, pulsa **Cargar catálogo piloto**. Optimus valida los dos archivos públicos incluidos e importa los ocho resúmenes mediante el CLI real, en un directorio temporal propio. Solo después de verificar el arranque del servicio muestra **Piloto público · 8 documentos**. Es un corpus finito en español, no toda Internet. Prueba `contraste`, `Entra` o `presupuestos`.

La selección se aplica a las pestañas de esta aplicación y dura únicamente la sesión. **Restaurar catálogo anterior** vuelve al índice habitual sin reemplazarlo. Al cerrar, la selección no se guarda. No se importan perfiles, historial o marcadores. Los marcadores normales siguen combinándose localmente en pestañas normales; las privadas no reciben esos marcadores. Abrir un resultado público inicia navegación al sitio correspondiente y requiere red, aunque buscar en el índice sea local.

Un archivo público ausente/modificado, importación fallida, cancelación o arranque no verificado muestra un error y conserva la selección anterior. Un servicio independiente no se detiene ni reconfigura: ciérralo por su vía habitual antes de cargar el piloto. Un fallo de cierre del servicio propio impide confirmar el cambio; sigue el aviso y reinicia Optimus. La aplicación no borra índices previos. Solo limpia archivos temporales propios cuando el cierre del proceso permite confirmarlo; entradas ajenas o enlaces inesperados se conservan.

Los archivos fijos son `Search/catalog/public-pilot-v0.1.json` y su procedencia. Sus hashes conocidos vinculan los resúmenes revisados; no certifican los bytes de los artículos remotos, aval de Microsoft o detección automática de información privada. Consulta [la procedencia y cobertura](../../search/docs/PUBLIC_PILOT.md). No hay rastreo, descarga de fuentes ni actualización automática.

## Pruebas y límites

Las pruebas portables usan el importador CLI real con el corpus incluido y comprueban selección/restauración, error, cancelación, servicio independiente y rechazo de cambios sin cierre normal. WPF y helper se compilan por separado; compilar desde Linux no es ejecutar Windows.

La aceptación nativa específica debe ejecutarse en un usuario/runner Windows desechable desde el workflow manual del piloto, con SHA literal de producto revisado. Prueba la interfaz real: ayuda habitual, carga válida, ocho consultas, fallo de recarga manteniendo una lectura exclusiva del archivo público (sin modificarlo), vacío real y restauración. El rechazo de bytes malformados se prueba aparte con el importador real en las pruebas portables. La apertura/renderizado de un resultado se comprueba aparte con un marcador loopback creado mediante la guía normal; no se presenta como descarga de un artículo público sin red. Se conservan TLS/HMAC, identidad de binarios y cierre normal. Un entorno no interactivo es bloqueado, no aprobado por inferencia.

La distribución histórica conserva las tres ayudas predeterminadas. El empaquetador existente permite los dos archivos públicos adicionales e inventaría sus hashes; la verificación nativa compara además sus bytes con las fuentes revisadas después de publicar los tres ejecutables. No se afirma que el validador antiguo de publicación haga obligatorios estos dos archivos opcionales.

Azure sigue siendo la infraestructura objetivo bajo2079, sin recurso ni coste activado aquí. El host permanece exclusivamente loopback con token por dispositivo; la búsqueda Web2062 y la futura identidad/servicio remoto mantienen sus criterios propios. El contrato compartido permanece disponible para Linux, sin atribuir aceptación a un cliente Linux aún no probado en este incremento.
