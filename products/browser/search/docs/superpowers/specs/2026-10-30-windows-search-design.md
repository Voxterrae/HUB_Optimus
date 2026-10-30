# Optimus Search local + Windows — incremento de #2021

## Intención y autorización

El usuario elige #2021 como coordinación y encarga continuar Windows con la búsqueda general y un primer índice propio acotado. Wikipedia pasa a ser una elección explícita. La implementación se presenta en PR pequeña, apilada sobre la importación #2018 mientras siga abierta. Linux conserva su encargo y autoría independientes; el servicio/protocolo será reutilizable. La delegación previa de detalles evita repetir preguntas o aprobaciones del mismo alcance.

## Enfoque

Mantener WPF/WebView2 y .NET10. Añadir un ejecutable local .NET/ASP.NET Core, sin paquetes nuevos externos, y un cliente nativo tipado. Frente a introducir Python/Node en el escritorio, reutiliza el runtime de distribución Windows. Frente a activar Azure/Dataverse/IA, entrega primero una búsqueda comprobable sin contratación. Un índice mundial propio y rastreo autónomo se dejan para otro incremento: aquí el operador importa contenido de forma explícita y el motor construye su índice y relevancia local. El agregado web depende de una instancia SearXNG controlada/configurada, no elegida silenciosamente.

## Contrato HTTPS v1 compartido

- Servicio escucha solo IPv4 loopback `127.0.0.1`, puerto predeterminado17831; `--port` permite0 en pruebas o1..65535. Ningún env/argumento puede abrir0.0.0.0 o una IP externa.
- `GET /health`: JSON exacto `{name:"OptimusSearch",version:1}`; sin consulta, token, corpus, métricas privadas ni URL upstream.
- `GET /search?format=json&q=...&scope=web|index&language=es`: requiere `Authorization: Bearer <token>`; rechaza cualquier Origin y Host no correspondiente al loopback/puerto real. No CORS, métodos de escritura ni archivos estáticos.
- Respuesta JSON: `{query,results:[{title,url,content,source}],optimus:{version:1,scope,webConfigured,indexedDocuments},error?,message?}`. Todos los textos remotos se mantienen inertes. El cliente valida marcador/protocolo; no etiqueta datos SearXNG arbitrarios como respuesta Optimus.
- Solo `scope=web` consulta el SearXNG fijo del operador. Endpoint admite HTTPS o HTTP con localhost literal o IP loopback, sin credenciales/query/fragmento. Conserva el prefijo del endpoint; `/instance`, `/instance/` y `/instance/search` solicitan `/instance/search?format=json&q=...&language=...&categories=general`; raíz usa `/search`. Sin red al escribir, sin red en index. Si no está configurado:503 `web-not-configured`. Fallo upstream (incluido unresponsive_engines no vacío, aunque haya resultados parciales):502; timeout:504; nunca sustitución por Wikipedia.
- Query1..500 UTF16, máximo20 resultados, URLs HTTP(S) absolutas sin credenciales/controles/backslash y máximo2048, título240, snippet1200. Deduplicación por URI normalizada sin fragmento, orden upstream conservado en web. Respuesta upstream1MiB, deadline10s incluye streaming/cancelación; redirecciones/cookies/credenciales ambientales desactivadas. Búsqueda cancelada no aplica resultados ni retiene streams.
- Errores de consulta400, token ausente/incorrecto401, Origin/Host403. Mensajes no reflejan token, URL configurada, contenido de archivos ni excepciones. Encabezados no-store/nosniff/no-referrer. Desactivar logs de solicitudes que puedan contener query/token.

## Token y procesos

Token local aleatorio32bytes representado por64hex, comparación constante. Predeterminado `LocalApplicationData/Optimus/Search/service.token`; se crea atómicamente,0600 en Unix, dentro del perfil de usuario en Windows. Un archivo existente inválido falla cerrado; no se sustituye silenciosamente. No se guarda en settings, Git, argumentos, paquetes o logs. El usuario/admin local conserva control de su perfil; no se afirma protección contra procesos comprometidos del mismo usuario ni administradores.

CLI `Optimus.SearchHost [--port N] [--index-file path] [--token-file path] [--searx-url URL]`. El launcher Windows lee el token de ese perfil y solo lo envía a la URL loopback fija; no lo transmite a SearXNG. Puede iniciar únicamente `Search/Optimus.SearchHost.exe` del mismo paquete, con ArgumentList/UseShellExecute=false. Conserva el proceso que inicia y termina solo ese proceso al cerrar. No mata servicios ajenos. Ajustes upstream cambiados requieren reiniciar/reconfigurar el proceso que le pertenece; si hay un servicio independiente, informa ese límite.

## Índice propio acotado

CLI `Optimus.SearchHost index --input catalog.json --output index.json` valida y escribe atómicamente un catálogo normalizado. Esquema `{schemaVersion:1,documents:[{url,title,content,source,updatedUtc}]}`. Máximo1000 documentos,64KiB de contenido por documento, archivo16MiB. URLs/títulos cumplen límites anteriores, fechas UTC válidas, contenido texto plano. Duplicados por URI normalizada se rechazan o consolidan determinísticamente (documentar elección). Entradas inválidas no publican un índice parcial.

Al arrancar, el host carga una instantánea del índice y construye búsqueda por tokens Unicode con relevancia BM25 determinista, título ponderado y desempate por URL. Buscar exige coincidencia de al menos un término; sin coincidencias devuelve vacío. No SQL/código/markup de entrada, aprendizaje de consultas, rastreo, historial ni caché de resultados. La distribución puede incluir ayuda pública de Optimus realmente indexada y claramente etiquetada, sin presentarla como cobertura de toda la web.

## Windows

La búsqueda Optimus predeterminada selecciona Web y el servicio local. El formulario permite elegir Web, Índice Optimus y Wikipedia. Introducir texto o cambiar opción cancela/invalida trabajo anterior sin emitir búsqueda nueva. Wikipedia solo por su elección explícita; no por ausencia/error del servicio. Conserva marcadores locales y límites actuales; pestañas privadas siguen excluyendo marcadores y sin persistir consultas/resultados. Buscar/Intro respetan la selección del formulario; el texto buscado desde la barra de direcciones selecciona Web explícitamente. Todas usan la misma frontera de elegibilidad/cancelación existente.

Añadir target tipado `OptimusSearchTarget(OptimusSearchScope Scope,string? Endpoint,string? BearerToken)` con enum Web/Index/Wikipedia; overloads de SearchService y SearchSubmissionGate. Conservar el overload legado de SearXNG para pruebas/compatibilidad, pero la aplicación nueva no lo usa como ruta predeterminada. El endpoint local por defecto es `https://127.0.0.1:17831`; secretos nunca se serializan. La UI expresa fuente, configuración ausente, errores y alcance del índice en lenguaje claro. No cuenta obligatoria, nuevo backend remoto, modificación de perfiles privados ni cambios en su barrera.

## Entrega y límites

Código bajo products/browser/search y cambios mínimos en products/browser/windows. Versionado de entrega0.3alpha sin firma, avisos/licencias .NET/ASP.NET/WebView2 conservados. Build/publish deben incluir host separado en Search/, ayuda y fuentes. Pruebas de motor, streams y API, suites nativas heredadas + nuevas, compilación WPF cross-target. Smoke end-to-end de servicio y cliente con resultados web genuinos si la red/proveedores lo permiten; distinguirlo de fixtures y nunca presentar respuesta vacía/irrelevante como aceptación.

No Azure/Dataverse, pagos, cuentas, roles, derechos, licencias del proyecto, workflows, firma/merge ni Linux runtime se activan/cambian. Aceptación de UI/micrófono/privacidad/red en Windows físico y firma siguen pendientes salvo prueba real posterior. Un servidor local/compilación Linux no los acredita.

## Cierre de identidad local (revisión de integración)

Un proceso de otro usuario podría ocupar17831 y copiar el marcador de health. Antes de enviar bearer/consulta, Windows verifica prueba de posesión del token del perfil. El cliente envía un nonce aleatorio32bytes/64hex mediante `X-Optimus-Nonce` en GET/health sin credenciales. El servidor devuelve `X-Optimus-Proof`,64hex de HMAC-SHA256 con clave ASCII del token64hex y mensaje ASCII exacto `OptimusSearch/v1|127.0.0.1:{puertoReal}|{nonce}`. Puerto real desde la conexión validada, no Host arbitrario; incluirlo impide reutilizar prueba de otro listener. Comparación constante y nonce fresco por conexión. Una respuesta sin prueba válida nunca habilita envío de bearer/query ni provoca matar el proceso independiente. Health sin nonce puede seguir devolviendo solo nombre/version para estado público; nonce inválido devuelve400 genérico, sin reflejarlo/logs. No protege contra procesos que ya lean el token del mismo usuario/administrador, límite previamente declarado.

## Corrección final autorizada: TLS en cada petición

La decisión final del integrador sustituye el transporte HTTP anterior por HTTPS exclusivo. La prueba de health por sí sola deja una carrera si otro usuario reemplaza el listener antes de search. Cada transporte real autentica un certificado autofirmado ECDSA P-256 efímero mediante HMAC-SHA256 de su SPKI, protocolo HTTPS y endpoint/puerto real; TLS estándar BCL acredita posesión de la clave privada. Esquema exacto de extensión y mensaje en [PROTOCOL.md](../../PROTOCOL.md). Cliente por petición con instantánea del token, sin fallback HTTP ni reutilización entre tokens; conexiones nuevas/reconectadas deben autenticar el certificado. Claves en memoria hasta cierre; sin certificados persistidos ni cambio del almacén de confianza. Certificado generado desde el puerto real de conexión tras bind, seguro también con puerto 0.

Pruebas reales obligatorias: servicio TLS y cliente nativo; sustitución entre health/search; reconexión con certificado incorrecto; proof/certificado público copiados sin clave; token/extensión ausente, malformada o incorrecta; cancelación y cero bearer/query al impostor. No cifrado propio de payloads.
