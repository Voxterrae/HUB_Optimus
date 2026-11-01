# Optimus Search — contrato HTTPS/CLI v1

Contrato vinculante: [diseño aprobado](https://github.com/Voxterrae/HUB_Optimus/blob/feat/browser-windows-search-2021/products/browser/search/docs/superpowers/specs/2026-10-30-windows-search-design.md). El host usa exclusivamente HTTPS en `127.0.0.1`, puerto 17831 por defecto; `--port` admite 0 para pruebas o 1..65535. No hay opción para abrir una interfaz externa.

| Operación | Contrato |
| --- | --- |
| `GET /health` | JSON exacto `{"name":"OptimusSearch","version":1}` sin información de token, catálogo ni upstream. El cliente solicita prueba mediante nonce antes de enviar credenciales. |
| `GET /search?format=json&q=texto&scope=web&language=es` | `Authorization: Bearer <token>`; scopes `web` e `index`. Rechaza Origin y Host que no corresponda a loopback/puerto real. |
| Respuesta | `{query,results:[{title,url,content,source}],optimus:{version:1,scope,webConfigured,indexedDocuments},error?,message?}`. |
| CLI de servicio | `Optimus.SearchHost [--port N] [--index-file path] [--token-file path] [--searx-url URL | --web-provider mwmbl] [--owner-stdin true]`. La última opción exige entrada estándar redirigida y reserva EOF para el cierre del proceso propio. |
| CLI de importación | `Optimus.SearchHost index --input catalog.json --output index.json`. |

No CORS, endpoints de escritura ni archivos estáticos. Encabezados no-store, nosniff y no-referrer. No logs de solicitudes que revelen consulta/token. Textos externos inertes. El cliente comprueba el marcador Optimus y la versión; una respuesta arbitraria SearXNG no es una respuesta Optimus.

Con `--searx-url`, `web` envía `/search?format=json&q=...&language=...&categories=general` únicamente al endpoint SearXNG fijo del operador. Conserva el prefijo configurado: `/instance`, `/instance/` y `/instance/search` usan `/instance/search`; raíz usa `/search`. HTTPS o HTTP con `localhost` literal o una IP loopback (sin confiar en otros nombres DNS); sin credenciales, query ni fragmento configurados. Redirecciones, cookies y credenciales ambientales desactivadas; máximo 1 MiB y plazo total 10 s incluyendo cuerpo. `index` no hace solicitudes de red. Escribir/cambiar fuente en Windows invalida trabajo anterior sin enviar otra búsqueda.

| Límite / error | Resultado |
| --- | --- |
| Consulta | 1..500 unidades UTF-16. |
| Resultados | Máximo 20; URL HTTP(S) absoluta <=2048, título <=240, contenido <=1200. Sin credenciales/controles/backslash en URL. |
| Duplicados web | URI normalizada sin fragmento; conserva el orden upstream. |
| Consulta inválida | 400. |
| Token ausente/incorrecto | 401. |
| Origin/Host rechazado | 403. |
| Web sin configurar | 503, `web-not-configured`. |
| Cuota o frecuencia externa agotada | 429, `upstream-rate-limited`; mensaje genérico, sin resultados ni reintento automático. |
| Fallo upstream / timeout | 502 / 504; mensajes no revelan URL, token, archivos ni excepciones. `unresponsive_engines` no vacío (o de tipo inválido) devuelve 502 incluso si hay resultados parciales; vacío sano devuelve 200. |

## Proveedor Mwmbl opcional

`--web-provider mwmbl` selecciona únicamente el piloto Mwmbl y es incompatible con `--searx-url`. Un valor desconocido o una opción repetida falla al arrancar. Sin ambas opciones no se configura Web. El protocolo local sigue en versión 1; `webConfigured` indica selección de proveedor, no su disponibilidad, cuota o calidad. El launcher y las preferencias nativas existentes no activan esta opción automáticamente.

La petición externa es un GET HTTPS al endpoint fijo `https://api.mwmbl.org/api/v2/search/?q=...`, con consulta escapada y sin bearer local, clave API, cookies, credenciales HTTP ambientales o redirecciones. Mwmbl recibe la consulta y la IP de salida. No existe fallback ni reintento. `language` se valida como antes en el host, pero el adaptador no lo envía a Mwmbl ni promete filtro por idioma o SafeSearch.

El JSON debe ser un objeto con `results` de tipo array y sin `error` no nulo. El máximo es 1 MiB y profundidad 32. Filas sin URL válida o título no vacío se omiten; contenido ausente o no textual se trata como vacío. Se normaliza y deduplica la URL, se conserva el orden externo y se devuelven como máximo 20 resultados válidos, con título de hasta 240 unidades UTF-16 y contenido de hasta 1200. Los textos continúan siendo datos inertes.

| `engine` externo reconocido | `source` de Optimus |
| --- | --- |
| `mwmbl` | `Mwmbl · índice` |
| `user` | `Mwmbl · comunidad` |
| `wikipedia` | `Mwmbl · Wikipedia` |
| `google` | `Mwmbl · Google` |
| Ausente o no reconocido | `Mwmbl · origen no especificado` |

La separación mínima entre inicios de peticiones externas es 1,1 s, coordinada entre las instancias del mismo proceso. El turno se conserva hasta disponer la respuesta. El límite total de 10 s incluye espera, conexión, cabeceras y cuerpo; la espera y la lectura son cancelables. Esto no coordina otros procesos ni equipos de la misma IP y no reserva o contabiliza una cuota mensual. HTTP 429 se propaga como el error local de cuota de la tabla; otros estados no satisfactorios, esquemas inválidos y redirecciones fallan sin resultados.

El acceso anónimo publicado el 01/11/2026 indica 1.000 consultas/mes, 1/s por IP y ningún SLA. No se crea cuenta ni se activa facturación. Las condiciones combinan permiso de aplicación comercial y resultados CC BY-NC-SA 4.0: no se infiere autorización comercial de los resultados. Piloto privado y finito; despliegue comercial y reutilización pendientes de aclaración, sin importar resultados al índice. Fuentes: [acceso](https://developer.mwmbl.org/) y [condiciones](https://developer.mwmbl.org/terms/).

La respuesta es de un proveedor externo; no acredita índice mundial propio, cobertura completa, relevancia ni protección de contenidos. La [validación del piloto](VALIDATION_MWMBL_PILOT.md) distingue pruebas controladas, consultas reales mediante el cliente y aceptación nativa Windows.

Token aleatorio de 32 bytes, 64 hexadecimales, comparación constante; se crea atómicamente en el perfil (0600 en Unix). Un archivo existente inválido falla cerrado. La creación entre procesos cooperantes se serializa mediante service.token.lock vacío y persistente (0600 en Unix), exclusión verificada y espera cancelable de hasta cinco segundos. Se comprueba de nuevo el destino bajo el guard; no se borra el sidecar, evitando separar propietarios entre inodos. Si la exclusión no está disponible, no se publica un token. Nunca se envía a SearXNG ni se serializa en settings, argumentos, paquetes o logs. No se afirma aislamiento frente a procesos comprometidos del mismo usuario o administradores.

El catálogo de importación es `{schemaVersion:1,documents:[{url,title,content,source,updatedUtc}]}`, máximo 1000 documentos, 64 KiB UTF-8 por contenido y 16 MiB por archivo. Fecha UTC y URL/título válidos; importación atómica, nunca parcial. El motor construye un índice real determinista BM25 con términos Unicode, título ponderado y empate por URL. Una URI canónica duplicada, incluso con fragmento distinto, rechaza toda la importación.

Windows inicia solo el `Search/Optimus.SearchHost.exe` de su paquete, con ArgumentList y UseShellExecute=false. Lee el token del perfil, lo usa solo para loopback y conserva/termina únicamente su propio proceso. Un servicio independiente no se mata. Wikipedia es una elección explícita y no un scope del host. No hay fallback silencioso entre Web, Índice y Wikipedia.

## Prueba de identidad antes del bearer

Windows envía `X-Optimus-Nonce` (32 bytes aleatorios, 64 hex) en GET /health sin Authorization. El host devuelve `X-Optimus-Proof`: HMAC-SHA256 en 64 hex, clave ASCII del token64hex, mensaje ASCII exacto `OptimusSearch/v1|127.0.0.1:{puertoReal}|{nonce}`. El puerto procede de la conexión real validada, no de un Host libre. El cliente usa nonce fresco y comparación constante y conserva exactamente el token cuya posesión verificó. Sin prueba válida no devuelve target/bearer ni envía consulta; no mata el proceso independiente. Esto impide copiar el marcador o reutilizar la prueba de otro puerto, pero no protege frente a procesos que ya lean el token del mismo perfil ni administradores.

Health sin nonce mantiene solo el JSON de estado. Nonce malformado:400 con `{"error":"invalid-request","message":"Invalid request."}`, sin reflejar valores ni registrarlos. Un nombre/version compatible por sí solo indica ocupación del puerto, no identidad.

## Autenticación de cada transporte TLS (rige sobre el diseño HTTP anterior)

El endpoint Windows es `https://127.0.0.1:17831`; no existe fallback HTTP. La creación del certificado autofirmado ECDSA P-256 ocurre en el selector TLS después del bind, usando el puerto local real de la conexión (incluido `--port 0`), y se conserva hasta detener el host. En Linux la clave permanece en memoria. En Windows, Schannel rechaza las claves efímeras de esta implementación con `0x8009030E`, observado en el run 41327022528: el host utiliza un contenedor CNG individual del usuario actual, de uso firma y con exportación privada deshabilitada. Windows persiste ese contenedor durante su vida; no se afirma memoria exclusiva. No se exporta la clave privada, no se instala el certificado en un almacén de certificados o confianza y no se cambian permisos del sistema.

El propietario del certificado conserva la clave, elimina explícitamente el contenedor CNG al cerrar y falla si no confirma su limpieza. Una instancia cerrada no puede emitir otra identidad. El navegador y el diagnóstico abren una tubería stdin únicamente para su proceso propio; EOF solicita cierre normal y permite liberar certificado y clave. No hay endpoint HTTP de apagado ni control sobre servicios independientes. El cierre está acotado; si requiere terminación forzada o el proceso sale con error, se informa que la limpieza no está verificada y se bloquea la reconfiguración del proceso propio. Un crash, pérdida de energía, terminación forzada o fallo de borrado pueden dejar una clave huérfana; no se promete borrado tras esos eventos ni se borran claves ajenas en el arranque. Los procesos del mismo usuario y administradores continúan fuera de la frontera de aislamiento ya declarada.

El certificado lleva exactamente una extensión no crítica OID `1.3.6.1.4.1.57264.2021.1`. Sus bytes son exactamente los 32 bytes de HMAC-SHA256 (sin envoltura ASN.1 adicional ni texto hexadecimal). Clave HMAC: los 64 bytes ASCII del token de perfil, conservando mayúsculas/minúsculas. Mensaje ASCII exacto: `OptimusSearch/TLS/v1|https://127.0.0.1:{puertoReal}|{SPKI}`; `SPKI` es Base64 estándar de DER SubjectPublicKeyInfo de esa clave ECDSA. Sin espacios ni salto final. Este dominio es distinto del challenge health.

Windows crea un transporte dedicado por petición local con la instantánea de token correspondiente y lo destruye al acabar. Antes de cualquier cabecera HTTP, TLS exige posesión de la clave privada y el cliente comprueba esquema/host/puerto, validez temporal, clave ECDSA de 256 bits, extensión única de 32 bytes y HMAC en tiempo constante. La confianza del perfil sustituye la cadena PKI pública; no existe callback que acepte cualquier certificado. Reconexiones vuelven a autenticar la clave con esa misma instantánea; no se reutilizan conexiones entre peticiones/tokens. Copiar el certificado/proof sin clave privada o cambiar el listener entre health y search no permite recibir bearer ni consulta.

Health sigue sin Authorization; su nonce HMAC es una comprobación adicional. Un fallo TLS produce error genérico y ninguna petición HTTP al impostor. Cancelación cierra el transporte y cuerpo pendientes. Los procesos que ya pueden leer el token de perfil y los administradores siguen fuera de este aislamiento.
