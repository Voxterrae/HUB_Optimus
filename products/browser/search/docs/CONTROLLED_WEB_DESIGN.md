# Fuente Web controlada — propuesta técnica revisable

Fecha de revisión: 7 de noviembre de 2026, Europe/Madrid. Asistencia de Codex.
Base examinada: `main@0a1dde5c47be9076973478cfb568a2a8219c3fdb`.
Estado: propuesta local; sin integrar, sin instalación, sin proveedor activado.

## Decisión y alcance

Preparar el proveedor SearXNG existente para un primer piloto privado en equipo
existente, con consultas explícitas y límites. Preferir Windows + WSL2 si ya está
disponible y tiene memoria suficiente; usar el Linux existente si esa condición
falla. La preferencia Microsoft se mantiene en el cliente .NET/Windows y en el
destino Azure posterior. Contratar alojamiento ahora no corrige la relevancia.
Esta elección es una recomendación técnica, no una decisión de despliegue.

La entrega endurece el transporte existente y documenta infraestructura,
privacidad, costes, evidencia y aceptación. No cambia la fuente predeterminada,
la interfaz, el catálogo, el ranking, TLS/HMAC, la configuración de usuario,
los workflows, las protecciones ni la dirección híbrida de Brave. No configura
motores nuevos ni repite el ensayo externo de #2062.

## Estado verificado y límites de la evidencia

| Pieza | Observación | Consecuencia |
| --- | --- | --- |
| Windows | `PrivacySettingsDialog` guarda `SearxEndpoint`; `SearchHostLauncher` lo pasa mediante `ArgumentList --searx-url` al hijo propio | La conexión de configuración ya existe; no falta otro cuadro de configuración |
| SearchHost | `Program` crea `SearxSearchProvider` solo si recibe el argumento | Sin endpoint, Web devuelve 503 `web-not-configured`; es el comportamiento correcto |
| Índice | Catálogo finito en memoria, BM25, máximo 1000 documentos / 16 MiB | Ocho referencias y tres ayudas no equivalen a cobertura web |
| #2062 | Run 42384253093: Python `topicMatched:true`, `officialDomain:null`, `pairedMatch:false`; Firefox no ejecutado por fail-fast | Sigue bloqueado por relevancia, sin demostrar CAPTCHA, HTTP429 ni caída de transporte |
| #2062, versiones | Producto `0790e0977c170ff8507bb73e0ec7b6e166755892`, workflow `0a1dde5c47be9076973478cfb568a2a8219c3fdb`, SearXNG `8b35dcd2e312d1d30fcfcbf6a9d01bda6fc52192` | No es aceptación del candidato Windows `91ce4863…` ni de esta entrega |
| #2098 | PR abierta, head `d77e2b5595235108e35142a2e8da799e5faa7218`; API remota independiente | Ocho referencias, sin buscador general ni integración automática con Web |
| #2108/#2109 | Dirección híbrida documentada: índice propio + Web Brave explícita | Conservarla como vía paralela; esta propuesta no la sustituye |
| #2111/#2114 | Adaptador y gateway Brave inactivos, sin integración Windows ni servicio público demostrado | Reutilizables tras revisión; no se presentan como servicios activos |

Fuentes del proyecto: [prueba manual Windows](https://github.com/Voxterrae/HUB_Optimus/issues/2021#issuecomment-6698395794),
[#2062](https://github.com/Voxterrae/HUB_Optimus/issues/2062),
[run 42384253093](https://github.com/Voxterrae/HUB_Optimus/actions/runs/42384253093),
[#2098](https://github.com/Voxterrae/HUB_Optimus/pull/2098),
[#2108](https://github.com/Voxterrae/HUB_Optimus/issues/2108),
[#2109](https://github.com/Voxterrae/HUB_Optimus/pull/2109),
[#2111](https://github.com/Voxterrae/HUB_Optimus/pull/2111),
[#2114](https://github.com/Voxterrae/HUB_Optimus/pull/2114).

## Comparación de alternativas

| Alternativa | Qué controlamos | Coste y dependencia | Uso recomendado |
| --- | --- | --- | --- |
| SearXNG privado en equipo existente | Proceso, configuración, motores disponibles, registros y acceso | Sin nueva cuota si hay capacidad; electricidad, conexión y mantenimiento siguen existiendo. Motores externos controlan sus índices y disponibilidad | Primer piloto del Web actual, sujeto a motores y relevancia aceptados |
| SearXNG en Azure Container Apps Consumption | Imagen y configuración bajo nuestro control; plataforma Microsoft | Franquicia compartida por suscripción; red y recursos auxiliares pueden facturar | Aplazar hasta medir consumo, asegurar acceso y cotizar |
| Brave API + gateway de #2114 | Adaptador, credencial del servidor, admisión y contabilidad local | Índice externo; plan, tarjeta, crédito, condiciones de uso y retención del proveedor | Opción paralela si SearXNG no logra relevancia; aprobación separada |
| Índice propio acotado | Adquisición autorizada, documentos, ranking, revisión y actualización | Sin API de búsqueda por consulta, pero con costes de rastreo, disco, CPU y operación | Independencia gradual con cobertura declarada, no promesa de Internet completo |
| Azure AI Search | Índice de los documentos que le ingiramos | No aporta un índice mundial; límites del nivel y posible gasto | Evaluar cuando el volumen supere el índice local; no necesario para este piloto |
| Bing API clásica / Foundry Grounding | Servicio externo Microsoft | Bing Search APIs se retiraron el 11/08/2025; Grounding requiere otro contrato con modelos y costes | No es sustitución directa gratuita del protocolo SearchHost |

SearXNG es **metabúsqueda**: controla el intermediario, no los índices ajenos.
Un índice verdaderamente propio exige obtener contenido permitido, conservar su
procedencia, indexarlo y actualizarlo. El catálogo actual sí tiene búsqueda
propia sobre un corpus finito; no tiene rastreador ni cobertura de la web general.

Brave publica actualmente Search a 5 USD/1000 solicitudes con 5 USD de crédito
mensual. Una prueba de dos llamadas supone 0,01 USD de consumo nominal y cien
llamadas 0,50 USD, antes del crédito y sujeto a la cuenta/plan. Exige tarjeta;
un plan antiguo postpago y uno nuevo prepago no tienen la misma exposición.
No se activa plan, clave ni recarga. Su ayuda prohíbe conservar datos recibidos
sin acuerdo aplicable; su aviso permite retener consultas hasta 90 días.
No importar resultados Brave al índice ni guardar respuestas como evidencia
sin derechos verificados. No afirmar retención cero.

## Arquitectura propuesta

El navegador conserva su SearchHost HTTPS en `127.0.0.1:17831`, con token de
perfil y autenticación TLS/HMAC. El host consulta únicamente al SearXNG elegido.
SearXNG consulta exclusivamente motores de una lista aprobada. El índice propio
permanece local y no hace peticiones de red. No hay sustitución silenciosa entre
fuentes ni conexión de la API de catálogo #2098 al scope Web.

| Tramo | Configuración prevista | Condición |
| --- | --- | --- |
| Windows → SearchHost | HTTPS loopback actual, bearer del perfil y TLS/HMAC | Nunca exponer el host ni compartir su token con otro equipo |
| SearchHost → SearXNG en WSL2 | Puerto loopback separado, por ejemplo `http://127.0.0.1:18888` | Comprobar desde Windows que localhost funciona y que no es accesible desde LAN |
| SearchHost → Linux existente | Túnel privado autenticado que termine en loopback en ambos extremos, o HTTPS privado autenticado revisado | El proveedor actual no lleva bearer remoto; no publicar SearXNG sin control de acceso |
| SearXNG → motores | HTTPS validado, lista de motores/destinos fijada, sin rotación de identidad ni reintentos | Aprobación de condiciones, privacidad, idiomas y límites de cada motor |
| Azure posterior | Ingreso HTTPS y autenticación remota propios, separados del perfil local | No conectar el cliente actual a un endpoint público anónimo |

Microsoft documenta el acceso Windows→WSL2 por localhost. WSL no se ha instalado
ni comprobado en el PC: memoria libre, virtualización, distribución, versión y
conectividad son bloqueos de preflight. Instalar WSL puede requerir privilegios
y reinicio. No presupuestar capacidad libre: un intento Windows reciente ya
documentó falta de memoria. Un piloto en Linux requiere verificar también
RAM, disco, titularidad operativa y acceso privado.

## Infraestructura, dependencias y configuración

Para desarrollo aislado: SDK .NET `10.0.403` ya disponible, framework ASP.NET
compartido y proyectos existentes, sin añadir NuGet ni SDK de motores. Para
producción, runtime/imagen mantenidos y revisados antes de su uso.

Para SearXNG: fuente oficial fijada por commit o imagen oficial por digest,
Python compatible, dependencias directas y transitivas bloqueadas con hashes,
inventario/SBOM, licencias/avisos aplicables y revisión de vulnerabilidades.
El pin histórico `8b35dcd…` es evidencia de #2062, **no aprobación automática**
de una imagen actual. El pip report de aquel ensayo no es un lock hermético.
No resolver `latest` ni instalar nuevas dependencias durante esta entrega.

Configuración a materializar solo después de elegir y revisar los motores:

| Ajuste | Valor requerido para el primer piloto |
| --- | --- |
| Bind / acceso | `127.0.0.1:18888`; `public_instance:false`; sin firewall público, DNS ni NAT nuevo |
| Engines | `use_default_settings.engines.keep_only` con lista exacta y no vacía revisada; eliminar todos los motores no aprobados del conjunto cargado |
| JSON | `search.formats:[json]` y POST en `/search` |
| Búsqueda segura | `safe_search:2`; comprobar soporte efectivo del motor, no inferirlo del parámetro |
| Solicitudes auxiliares | `autocomplete:""`, `favicon_resolver:""`, `image_proxy:false`; plugins no necesarios fuera |
| Privacidad | `debug:false`, métricas y access/body/query logs desactivados; sin cookies ni cabeceras del usuario reenviadas |
| Timeout / retry | Motor y global ≤8 s; `retries:0`, `retry_on_http_error:false`, TLS verificado; host mantiene límite total 10 s |
| Secreto | Aleatorio, fuera de Git y argumentos; archivo/entorno privado del proceso; no token de SearchHost |
| Aislamiento | Usuario sin privilegios, CPU/RAM/PID medidos y limitados, raíz solo lectura si el empaquetado lo admite; temporales privados y limpieza al parar |
| Admisión inicial | Un usuario, un ensayo serial de dos consultas y plazo de 15 min; sin servicio general continuo |

`disabled:true` no basta como allowlist: directivas `!bang` pueden seleccionar
motores/categorías que siguen cargados. Verificar el conjunto efectivo y probar
directivas contra destinos sintéticos antes del piloto. Si un motor devuelve
CAPTCHA, 429, denegación, error, vacío o irrelevancia: parar y registrar bloqueo;
sin evasión, rotación, nuevo motor automático ni relajación de aceptación.

**Selección upstream pendiente:** Mwmbl es el candidato histórico reproducible,
pero no ha superado la relevancia. Su documentación señala índice pequeño y
ausencia de soporte de idioma, región y safe-search. No se puede ofrecer hoy
como proveedor general o familiar aceptado. Otros motores exigirán verificar
sus condiciones y disponibilidad; no se configura uno por conjetura.

## Cambios reversibles y privacidad de esta entrega

El proveedor conserva el contrato local v1 y `source:"SearXNG"`. Cambia únicamente
el transporte hacia el operador: POST a la ruta fija, formulario con `format`,
`q`, `language`, `categories=general` y `safesearch=2`. Valida idioma antes de
red; rechaza tipo de contenido no JSON, codificación de cuerpo no admitida y
propiedades duplicadas ambiguas. Mantiene 1 MiB, profundidad 32, diez segundos,
20 resultados, deduplicación, filtros URL y errores genéricos, sin reintentos.

POST elimina la consulta de la URL **de ese tramo**. Windows→SearchHost sigue
siendo GET local autenticado y la sobrecarga antigua directa de compatibilidad
del cliente sigue sin cambiar. POST no oculta la consulta a SearXNG, sus motores
ni a un registro de cuerpos. El servidor y proxy controlados deben evitar
registrarla. No prometer anonimato absoluto ni certificación legal por diseño.

El proveedor no descarga los destinos de resultados: los enlaces a IP privadas
son un riesgo de navegación pendiente, no SSRF de descarga en este host. Se
conserva la validación existente sin cambiar las URLs legítimas del índice.
Antes de distribución pública, revisar destinos privados/reservados y pruebas
de navegación como incremento separado. Los textos externos se tratan como
contenido inerte; una URL segura no garantiza un sitio seguro.

Revertir el parche restaura el comportamiento anterior. En un piloto futuro,
vaciar `SearxEndpoint` mediante el flujo de ajustes y reiniciar solo el hijo
propio restaura 503 de Web; el índice sigue disponible. Un host independiente
se reconfigura por su operador. Parar únicamente procesos/contenedores propios,
comprobar ausencia de listener y limpiar solo temporales propios. No borrar el
perfil, catálogo, tokens o claves ajenos como medida de recuperación.

## Procedencia verificable

El `source` identifica al adaptador, no prueba la verdad del artículo ni el
motor concreto. El v1 descarta `engines` por resultado; se preserva por
compatibilidad. Para la primera aceptación, usar configuración de **un solo
motor** revisado y acreditar que la instancia cargó solo ese motor; un conjunto
multimotor necesita evidencia por resultado o una ampliación revisada del
contrato antes de afirmar atribución específica.

Registrar por ejecución: commit/tree de producto y harness por separado,
ProductVersion de navegador y host, SearXNG commit/digest, hash de configuración
sin secretos, hashes del lock/SBOM, motor y endpoint aprobados, UTC del ensayo,
ID de caso fijo, HTTPS/dominio oficial comprobado, `sourceVerified`,
`topicMatched`, `pairedMatch`, código de error cerrado y cierre/limpieza. Publicar
solo evidencia curada; no consultas personales, tokens, IP de usuario, rutas de
perfil ni respuestas brutas. Capturas/digests permitidos no sustituyen derechos
de retención ni autenticidad del contenido. No añadir rastreo a los logs.

## Índice verdaderamente propio: siguiente proyecto acotado

Comenzar por dominios propios/autorizados y feeds o sitemaps revisados, con
cobertura y fecha visibles. Hacen falta: permisos/condiciones, robots y políticas
de rastreo, cola de semillas, rate-limit por sitio, descargas acotadas,
redirecciones y DNS protegidos contra redes privadas/reservadas/rebinding,
parsing de texto aislado, deduplicación/canonicalización, idioma, revisión,
timestamps, hash de documento y revisiones, actualización/borrado y evaluación
de ranking. No mezclar material privado LCDH ni resultados licenciados de APIs.

La primera fase puede generar un catálogo compatible con el límite actual de
1000 documentos, mediante importación explícita y sidecar de procedencia. Para
crecer, diseñar otro servicio/indexador; no ampliar silenciosamente SearchHost
ni afirmar cobertura mundial. Este trabajo no incorpora un crawler ni realiza
descargas de páginas.

## Costes y acciones pendientes de aprobación

| Fase | Acciones exactas previstas | Coste previsto / condición |
| --- | --- | --- |
| Esta entrega | Editar copia aislada, compilar con SDK existente, ejecutar fixtures loopback, entregar diff y documentación | Ningún recurso Azure, suscripción o consulta de proveedor creado; sin compra ni nuevo servicio |
| Piloto local futuro | Elegir un equipo; comprobar capacidad; instalar solo dependencias/digest revisados si faltan; configurar SearXNG loopback con un motor; configurar endpoint del candidato; dos consultas públicas fijas; detener y revertir | 0 € de nuevas cuotas solo si hardware, red y software necesarios ya existen; electricidad/tiempo aparte. Aprobar equipo, instalaciones, motor y ventana antes de hacerlo |
| Azure futuro | Verificar suscripción/oferta/región; cotizar; revisar imagen; proponer grupo aislado, entorno ACA Consumption, app privada/autenticada y configuración de parada/limpieza | Importe EUR todavía **sin cotizar**; no autorizar ni ejecutar con este documento |
| Brave futuro | Revisar cuenta/plan/términos/privacidad; crédito disponible; límite proveedor y recarga desactivada; credencial solo servidor; dos intentos | Consumo nominal 0,01 USD antes de crédito; cargo efectivo y posible retención de tarjeta por verificar; aprobación separada |

ACA ofrece por mes/suscripción 180000 vCPU-s, 360000 GiB-s y 2 millones de
solicitudes HTTP. Se comparten con otros usos. Ejemplo aritmético, no tamaño
validado: **0,5 vCPU y 1 GiB totales durante 900 s = 450 vCPU-s y 900 GiB-s**,
más arranque/parada. No confundir veinte consultas con quince minutos reales de
réplica ni sumar componentes fuera de esa asignación. No hay cotización EUR
verificada para la oferta y región de esta cuenta.

Antes de pedir aprobación Azure, entregar un diff/plan de recursos con nombres,
región, SKU, imagen por digest, identidad/RBAC, ingress/auth, secretos, todas las
réplicas/revisiones, cuotas compartidas libres y tarifas efectivas en moneda de
facturación. Incluir CPU/RAM medidos, duración, requests, egress, registro,
almacenamiento, red privada y telemetría; separar coste fijo y variable. Evitar
crear ACR, Log Analytics, Key Vault, IP/NAT o private endpoint por defecto.
La alternativa privada elegida también necesita una cotización real.

Proponer `minReplicas:0`, `maxReplicas:1`, un solo revision activo y plazo de
parada; no son techo monetario. Un presupuesto Azure alerta y no corta consumo.
Desactivar almacenamiento de logs no elimina toda telemetría de plataforma.
No prometer 0 € si la suscripción no garantiza el límite. Si la exigencia sigue
siendo cero exposición a gasto adicional, mantener el piloto en equipo existente.

## Condiciones de primera aceptación

1. Revisión humana del diff y encaje con #2062/#2108; issue/PR específicos,
   commits verificados, checks obligatorios y conversaciones resueltas antes de
   integración. Esta copia local no es un commit oficial firmado ni un CI PASS.
2. Tests aislados del proveedor y regresiones del cliente/índice satisfechos;
   sin salida externa. Imagen, lock, configuración y acceso privado revisados.
3. Selección explícita del equipo, motor, responsable, privacidad, coste y
   ventana de prueba. Nueva aprobación exacta antes de instalación/servicio
   externo, consultas reales, Azure o gastos. No reutilizar autorización histórica.
4. Ensayo de inicio sin consultas: bindings correctos, JSON habilitado, logs
   revisados, TLS/HMAC, conjunto efectivo de motores, sin listener público.
5. En candidato exacto, cliente .NET tipado → host propio → SearXNG real:
   `Python programming` y `Mozilla Firefox`, secuenciales, sin bookmarks.
   Cada una requiere respuesta sin error, resultados no vacíos, source SearXNG
   y dominio oficial HTTPS + tema correcto **en el mismo resultado** dentro de
   los primeros 20. Un timeout/error/irrelevancia bloquea; no repetir ni compensar
   con otra fuente. Dos casos no acreditan búsqueda general.
6. Antes de prometer idiomas/cobertura, matriz ES/CA/DE/EN con consultas y
   destinos esperados fijados antes del ensayo, juicio humano sobre utilidad,
   consultas sin resultado y errores. Medir latencia, consumo y calidad; no usar
   LLM-as-judge ni cambiar umbrales después de observar el resultado.
7. Cierre normal, listener ausente, temporales propios limpios, reversión a
   índice/sin Web verificada y evidencia curada vinculada al SHA exacto.

Bloqueos abiertos: motor con relevancia suficiente; soporte real de idiomas y
safe-search; capacidad del equipo; lock transitivo y revisión de imagen;
atribución multimotor; acceso remoto/abuso si se comparte; aceptación Windows
nativa del nuevo SHA; cotización Azure. Ningún test sintético cierra #2062.

## Handoff y siguiente incremento

El handoff técnico de esta propuesta reside en este documento, el plan y la
validación adjunta. No se edita `docs/context/AI_HANDOFF.md` porque contiene
material protegido de autoridad fuera del alcance. `OWNER_AUTHORITY_HANDOFF.md`
permanece controlador, sin cambios. No se publica PR, servicio ni despliegue.
Siguiente incremento recomendado: revisar este parche, escoger equipo/motor y
preparar su manifest definitivo con coste y parada para aprobación humana.

## Referencias primarias externas

- [SearXNG Search API: POST/JSON](https://docs.searxng.org/dev/search_api.html).
- [Configuración de búsqueda](https://docs.searxng.org/admin/settings/settings_search.html).
- [Configuración y allowlist](https://docs.searxng.org/admin/settings/settings.html).
- [Motores y directivas](https://docs.searxng.org/admin/settings/settings_engines.html).
- [Límites de Mwmbl](https://docs.searxng.org/dev/engines/online/mwmbl.html).
- [Windows/WSL2 localhost](https://learn.microsoft.com/en-us/windows/wsl/networking).
- [Facturación ACA](https://learn.microsoft.com/en-us/azure/container-apps/billing).
- [Presupuestos Azure](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets).
- [Opciones de logs ACA](https://learn.microsoft.com/en-us/azure/container-apps/log-options).
- [Retirada Bing Search APIs](https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement).
- [Brave Search: precios](https://api-dashboard.search.brave.com/app/plans).
- [Brave: condiciones de retención y facturación](https://api-dashboard.search.brave.com/documentation/resources/help-feedback).
- [Brave: aviso de privacidad](https://api-dashboard.search.brave.com/documentation/resources/privacy-notice).
- [Azure AI Search: qué es un índice](https://learn.microsoft.com/en-us/azure/search/search-what-is-an-index).
- [Azure AI Search: límites](https://learn.microsoft.com/en-us/azure/search/search-limits-quotas-capacity).
