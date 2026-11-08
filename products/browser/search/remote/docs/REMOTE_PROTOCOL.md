# Optimus Remote Search API v1 — candidato revisable

Fecha: 4 de noviembre de 2026. Baseline de datos: `9fa3f8a0dbe5ea6919e49240a0df6bac7dbba803` (#2082). Contrato separado de `../../docs/PROTOCOL.md`: nunca enviar el token de un perfil local, usar sus pruebas HMAC ni cambiar SearchHost para apuntar a Internet.

## Transporte y compatibilidad

API HTTP/JSON UTF-8 sin SDK propietario, cookies, sesión compartida ni dependencia de una GUI. Windows, Linux y Android pueden implementar el mismo adaptador remoto. Este incremento no modifica ni acredita esos clientes nativos. La cobertura de datos sigue siendo un catálogo español finito.

En un servicio compartido el origen debe ser una URL HTTPS aprobada, con validación normal de cadena, nombre y vigencia del certificado. No se permite aceptar cualquier certificado, usar el canal de confianza del perfil ni reenviar credenciales en redirecciones. El cliente debe exigir el origen configurado, limitar respuestas a 64 KiB, permitir cancelar, no hacer reintentos automáticos de consultas ni alternar a otro proveedor sin una decisión explícita. La primera llamada tras escala a cero necesita un plazo de cliente compatible con arranque en frío; no confundir ese plazo con el límite interno de dos segundos.

El proceso candidato solo admite HTTP en loopback para pruebas, o en el puerto interno 8080 de un contenedor con opt-in explícito. TLS termina en un ingress Azure configurado con `allowInsecure=false`. Nunca exponer el puerto HTTP del contenedor fuera de esa frontera. Cabeceras de proxy, Host u Origin no conceden autenticación. No se usa `X-Forwarded-Proto` como prueba de identidad. La plantilla entregada mantiene ingress interno y no crea recursos.

## Autenticación del piloto

`Authorization: Bearer <credencial-remota>` en cada petición de búsqueda o catálogo. Credenciales opacas, individuales, generadas con 32 bytes aleatorios criptográficos y codificadas Base64url sin padding (43 caracteres). Son distintas de los tokens de SearchHost. El servidor guarda únicamente SHA-256 de la representación ASCII de la credencial, ID de cliente y caducidad UTC absoluta. No acepta JWT/Entra en esta versión ni los interpreta como credencial local.

Registro externo al código y a la imagen:

```json
{"schemaVersion":1,"clients":[{"clientId":"pilot-client-01","secretSha256":"HASH_SHA256_DE_UN_SECRETO_REMOTO_ALEATORIO","expiresUtc":"FECHA_UTC_HASTA_SIETE_DIAS"}]}
```

El ejemplo es deliberadamente inválido como configuración. No contiene un secreto utilizable. Registro de hasta 16 KiB, máximo 64 clientes; IDs ASCII de 1 a 64 caracteres y hashes únicos; comparación criptográfica en tiempo constante; rechazo de registros inválidos. La caducidad se comprueba también en cada petición. Para revocar, retirar la entrada y reiniciar con el registro revisado; para rotar, emitir otro secreto y redistribuirlo por canal privado. No introducir secretos en argumentos de proceso, URL, historial de terminal, telemetría, Git ni catálogo. La copia robada de un Bearer permite su uso hasta su revocación/caducidad: no se afirma vinculación criptográfica a dispositivo.

Guardar credenciales remotas en almacenamiento seguro de cada plataforma (protección de usuario/credenciales en Windows, secret service en Linux, Android Keystore mediante una clave que proteja el secreto de aplicación), sin reutilizar el archivo de token local. El mecanismo concreto de aprovisionamiento y almacenamiento del cliente queda para su incremento nativo. Una futura integración Entra/OIDC conservaría el transporte Bearer pero exigiría proveedor explícito, tenant/issuer/audience, firma, expiración y scope; nunca detección automática ni registro externo durante este trabajo.

## Endpoints

| Método/ruta | Autenticación | Comportamiento |
| --- | --- | --- |
| `GET /healthz` | No | Liveness mínimo; sin identidad, índice detallado ni estado de cuentas |
| `GET /v1/catalog` | Bearer remoto | Bytes exactos del catálogo y procedencia del release revisado |
| `POST /v1/search` | Bearer remoto | Búsqueda en las ocho referencias; no consulta Internet |

No admitir parámetros de URL en ninguna ruta, incluidos tokens o consultas. GET no admite cuerpo. POST exige `Content-Type: application/json` y cuerpo UTF-8 de hasta 2048 bytes. Objeto exacto con `query` y `limit`:

```json
{"query":"contraste","limit":3}
```

`query`: texto no vacío de hasta 500 unidades UTF-16, sin controles ni Unicode inválido. `limit`: entero de 1 a 8. Rechazar campos desconocidos, duplicados, tipos distintos, JSON malformado o demasiado profundo. No hay consulta GET, subida de documentos, importación, administración ni escritura remota.

Ambas respuestas de datos incluyen `schemaVersion=1`, `catalogId`, `catalogSha256` y `provenanceSha256`. `/v1/catalog` añade `catalogBytesBase64` y `provenanceBytesBase64`. `/v1/search` añade `results`, sin devolver el texto de la consulta. Cada resultado contiene `title`, `url`, `content`, `source`, `updatedUtc` y `provenance` (`referenceKind`, `referenceCheckedDate`, `sourceRevision`, `summarySha256`). `content` es el resumen propio completo que figura en el release; `[]` es un resultado vacío válido, sin fallback. Empates del ranking por URL ordinal del motor existente. No se infiere cobertura de toda Internet.

## Verificación independiente

| Material revisado | SHA-256 de bytes UTF-8 exactos |
| --- | --- |
| Catálogo | `8294911789f69f2c1262c80153ca0dddd6189e9a198b586f5fbb3beeb0d665ec` |
| Procedencia | `5312f482daea11727c9c90a683bcf95dce587021aa6c63609b9038756eb05aae` |

El servidor fija ambos hashes antes de abrir un listener y comprueba cada resumen. No aceptar una pareja catálogo/manifiesto modificada aunque sus hashes internos coincidan. Un cliente debe partir de estos hashes mediante un release de confianza; un hash enviado por el mismo servidor no autentica al editor por sí solo. Decodificar Base64, calcular SHA-256 de ambos archivos exactos, buscar cada URL, comparar todos los campos del documento y la entrada de procedencia, y calcular SHA-256 del `content` UTF-8. El verificador independiente `../tools/verify_response.py` implementa esta comprobación sin red. Rechaza también un catálogo atacante modificado con sus propios hashes consistentes.

La comprobación demuestra pertenencia e integridad del resumen del release, no verdad, relevancia, completitud, actualidad o bytes de las páginas referidas. Las seis referencias Microsoft son páginas vivas; las dos referencias HUB fijan su revisión histórica. `updatedUtc` y la revisión del catálogo describen nuestros resúmenes.

## Límites, privacidad y errores

Cuatro solicitudes de aplicación simultáneas, sin cola; límite global de admisión 120/minuto y 30/minuto por cliente autenticado. Límite interno de aplicación de dos segundos, cuerpo 2048 bytes, respuesta 64 KiB y máximo ocho resultados. Memoria del índice y de cuotas acotada por el release fijo y los 64 IDs. Los contadores son de proceso, se reinician al arrancar y pueden multiplicarse si hay réplicas solapadas durante mantenimiento. No constituyen cuota distribuida, defensa completa DDoS ni límite de gasto de Azure. La admisión anónima global puede ser agotada por abuso: el piloto es limitado y de invitación, no servicio público sin restricciones.

Sin conservación de consultas, perfiles, historial, marcadores, IP o tokens en la aplicación. Sin Application Insights, HTTP logging ni proveedor externo añadido. `Cache-Control: no-store`, sin CORS, sin cookies y errores genéricos; no incluir datos de entrada, rutas internas ni excepciones. Desactivar destino de logs de aplicación e ingress HTTP en Azure no prueba ausencia de registros internos de plataforma/seguridad de Microsoft.

Los errores generados por la aplicación tienen JSON exacto: `{"schemaVersion":1,"error":"CODIGO"}`. HTTP 400 `invalid_request`; 401 `unauthorized` con `WWW-Authenticate: Bearer`; 403 `forbidden` por Origin/Cookie; 404 `not_found`; 405 `method_not_allowed`; 408 `deadline_exceeded`; 413 `too_large`; 415 `unsupported_media_type`; 429 `rate_limited` o `busy`, con `Retry-After`; 500 `internal_error`. Liveness devuelve `{"status":"ok"}`. La descripción de máquina está en `openapi.json`. Kestrel puede rechazar HTTP malformado o límites de línea/cabeceras antes de la aplicación (por ejemplo 400, 414 o 431), con cuerpo vacío y sin las cabeceras de esta API. El cliente debe manejar ese estado sin exigir JSON ni devolver resultados vacíos. No presentar los errores de validación como resultados vacíos. Respetar `Retry-After` cuando se indique; no reintentar consultas automáticamente.

## Actualización y reversión

Release por imagen inmutable que fija código, catálogo y sidecar. No hay descarga, rastreo ni actualización automática. Un catálogo nuevo exige revisión de datos/procedencia, actualización de hashes, pruebas y nuevo digest de imagen. Revertir al digest anterior revisado con un registro de credenciales vigente; revocaciones no se revierten ni se resucitan con una imagen antigua. La recuperación de cuotas tras reinicio no es motivo para aumentar tráfico. Apagado y retirada de recursos requieren seguir el runbook Azure; poner la plantilla en false en modo incremental no borra un despliegue anterior.
