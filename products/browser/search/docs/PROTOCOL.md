# Optimus Search — contrato HTTPS/CLI v1

Contrato vinculante: [diseño aprobado](https://github.com/Voxterrae/HUB_Optimus/blob/feat/browser-windows-search-2021/products/browser/search/docs/superpowers/specs/2026-10-30-windows-search-design.md). El host usa exclusivamente HTTPS en `127.0.0.1`, puerto 17831 por defecto; `--port` admite 0 para pruebas o 1..65535. No hay opción para abrir una interfaz externa.

| Operación | Contrato |
| --- | --- |
| `GET /health` | JSON exacto `{"name":"OptimusSearch","version":1}` sin información de token, catálogo ni upstream. El cliente solicita prueba mediante nonce antes de enviar credenciales. |
| `GET /search?format=json&q=texto&scope=web&language=es` | `Authorization: Bearer <token>`; scopes `web` e `index`. Rechaza Origin y Host que no corresponda a loopback/puerto real. |
| Respuesta | `{query,results:[{title,url,content,source}],optimus:{version:1,scope,webConfigured,indexedDocuments},error?,message?}`. |
| CLI de servicio | `Optimus.SearchHost [--port N] [--index-file path] [--token-file path] [--searx-url URL]`. |
| CLI de importación | `Optimus.SearchHost index --input catalog.json --output index.json`. |

No CORS, endpoints de escritura ni archivos estáticos. Encabezados no-store, nosniff y no-referrer. No logs de solicitudes que revelen consulta/token. Textos externos inertes. El cliente comprueba el marcador Optimus y la versión; una respuesta arbitraria SearXNG no es una respuesta Optimus.

`web` envía `/search?format=json&q=...&language=...&categories=general` únicamente al endpoint SearXNG fijo del operador. Conserva el prefijo configurado: `/instance`, `/instance/` y `/instance/search` usan `/instance/search`; raíz usa `/search`. HTTPS o HTTP con `localhost` literal o una IP loopback (sin confiar en otros nombres DNS); sin credenciales, query ni fragmento configurados. Redirecciones, cookies y credenciales ambientales desactivadas; máximo 1 MiB y plazo total 10 s incluyendo cuerpo. `index` no hace solicitudes de red. Escribir/cambiar fuente en Windows invalida trabajo anterior sin enviar otra búsqueda.

| Límite / error | Resultado |
| --- | --- |
| Consulta | 1..500 unidades UTF-16. |
| Resultados | Máximo 20; URL HTTP(S) absoluta <=2048, título <=240, contenido <=1200. Sin credenciales/controles/backslash en URL. |
| Duplicados web | URI normalizada sin fragmento; conserva el orden upstream. |
| Consulta inválida | 400. |
| Token ausente/incorrecto | 401. |
| Origin/Host rechazado | 403. |
| Web sin configurar | 503, `web-not-configured`. |
| Fallo upstream / timeout | 502 / 504; mensajes no revelan URL, token, archivos ni excepciones. `unresponsive_engines` no vacío (o de tipo inválido) devuelve 502 incluso si hay resultados parciales; vacío sano devuelve 200. |

Token aleatorio de 32 bytes, 64 hexadecimales, comparación constante; se crea atómicamente en el perfil (0600 en Unix). Un archivo existente inválido falla cerrado. Nunca se envía a SearXNG ni se serializa en settings, argumentos, paquetes o logs. No se afirma aislamiento frente a procesos comprometidos del mismo usuario o administradores.

El catálogo de importación es `{schemaVersion:1,documents:[{url,title,content,source,updatedUtc}]}`, máximo 1000 documentos, 64 KiB UTF-8 por contenido y 16 MiB por archivo. Fecha UTC y URL/título válidos; importación atómica, nunca parcial. El motor construye un índice real determinista BM25 con términos Unicode, título ponderado y empate por URL. Una URI canónica duplicada, incluso con fragmento distinto, rechaza toda la importación.

Windows inicia solo el `Search/Optimus.SearchHost.exe` de su paquete, con ArgumentList y UseShellExecute=false. Lee el token del perfil, lo usa solo para loopback y conserva/termina únicamente su propio proceso. Un servicio independiente no se mata. Wikipedia es una elección explícita y no un scope del host. No hay fallback silencioso entre Web, Índice y Wikipedia.

## Prueba de identidad antes del bearer

Windows envía `X-Optimus-Nonce` (32 bytes aleatorios, 64 hex) en GET /health sin Authorization. El host devuelve `X-Optimus-Proof`: HMAC-SHA256 en 64 hex, clave ASCII del token64hex, mensaje ASCII exacto `OptimusSearch/v1|127.0.0.1:{puertoReal}|{nonce}`. El puerto procede de la conexión real validada, no de un Host libre. El cliente usa nonce fresco y comparación constante y conserva exactamente el token cuya posesión verificó. Sin prueba válida no devuelve target/bearer ni envía consulta; no mata el proceso independiente. Esto impide copiar el marcador o reutilizar la prueba de otro puerto, pero no protege frente a procesos que ya lean el token del mismo perfil ni administradores.

Health sin nonce mantiene solo el JSON de estado. Nonce malformado:400 con `{"error":"invalid-request","message":"Invalid request."}`, sin reflejar valores ni registrarlos. Un nombre/version compatible por sí solo indica ocupación del puerto, no identidad.

## Autenticación de cada transporte TLS (rige sobre el diseño HTTP anterior)

El endpoint Windows es `https://127.0.0.1:17831`; no existe fallback HTTP. Al iniciar el host se crea una clave ECDSA P-256 y certificado autofirmado efímeros en memoria. La creación ocurre en el selector TLS después del bind, usando el puerto local real de la conexión (incluido `--port 0`), y se conserva ese certificado hasta detener el host. Se libera la clave al cerrar; no se exporta, persiste ni añade a almacenes de confianza.

El certificado lleva exactamente una extensión no crítica OID `1.3.6.1.4.1.57264.2021.1`. Sus bytes son exactamente los 32 bytes de HMAC-SHA256 (sin envoltura ASN.1 adicional ni texto hexadecimal). Clave HMAC: los 64 bytes ASCII del token de perfil, conservando mayúsculas/minúsculas. Mensaje ASCII exacto: `OptimusSearch/TLS/v1|https://127.0.0.1:{puertoReal}|{SPKI}`; `SPKI` es Base64 estándar de DER SubjectPublicKeyInfo de esa clave ECDSA. Sin espacios ni salto final. Este dominio es distinto del challenge health.

Windows crea un transporte dedicado por petición local con la instantánea de token correspondiente y lo destruye al acabar. Antes de cualquier cabecera HTTP, TLS exige posesión de la clave privada y el cliente comprueba esquema/host/puerto, validez temporal, clave ECDSA de 256 bits, extensión única de 32 bytes y HMAC en tiempo constante. La confianza del perfil sustituye la cadena PKI pública; no existe callback que acepte cualquier certificado. Reconexiones vuelven a autenticar la clave con esa misma instantánea; no se reutilizan conexiones entre peticiones/tokens. Copiar el certificado/proof sin clave privada o cambiar el listener entre health y search no permite recibir bearer ni consulta.

Health sigue sin Authorization; su nonce HMAC es una comprobación adicional. Un fallo TLS produce error genérico y ninguna petición HTTP al impostor. Cancelación cierra el transporte y cuerpo pendientes. Los procesos que ya pueden leer el token de perfil y los administradores siguen fuera de este aislamiento.
