# Optimus Search — host local compartido v1

Servicio .NET/ASP.NET Core 10 para Web mediante un SearXNG controlado o el piloto externo Mwmbl seleccionado expresamente, y para un índice propio finito sin conexión. Forma parte del trabajo de #2021 y mantiene un protocolo reutilizable por Linux, sin modificar su trabajo. No crea cuentas, servicios de pago, Azure, Dataverse ni proveedores de IA.

```sh
dotnet run --project tests/Optimus.Search.Tests -c Release
dotnet run --project src/Optimus.Search/Optimus.Search.csproj -- --port 17831 --index-file /ruta/al/perfil/index.json --searx-url https://searx.example.org
dotnet run --project src/Optimus.Search/Optimus.Search.csproj -- index --input /ruta/catalog.json --output /ruta/al/perfil/index.json
```

La URL es un marcador que el operador sustituye por su instancia controlada. Los caminos de perfil están fuera del código y de los artefactos. Nunca se pasa el valor del token en argumentos. `--token-file` cambia la ruta del archivo de perfil; no acepta un token en texto. El predeterminado está en LocalApplicationData/Optimus/Search/service.token. El servicio usa exclusivamente HTTPS. Windows autentica la clave pública TLS mediante HMAC del token de perfil en cada conexión antes de enviar bearer o consulta; la prueba adicional de health no sustituye esa autenticación. Linux conserva la clave en memoria; Windows utiliza una clave CNG no exportable del usuario actual, persistida durante la vida del host y eliminada al cerrarlo normalmente. El certificado no se instala en almacenes de confianza. El cierre forzado puede dejar una clave huérfana; consulta [el contrato](docs/PROTOCOL.md). `--port 0` permite un puerto efímero en pruebas; siempre IPv4 loopback. `--owner-stdin true` se reserva al proceso hijo propio con entrada redirigida para su cierre por EOF; no añade un endpoint de apagado.

`catalog/optimus-help.json` contiene tres documentos breves redactados para esta entrega y etiquetados Ayuda Optimus. Build los importa mediante el CLI real al publicar: permiten probar «servicio local» o «importar documentos» sin configurar un catálogo propio. No son resultados web; las URLs señalan los documentos de la rama de entrega y las fechas identifican la versión de contenido, sin afirmar una descarga o verificación remota.

El índice predeterminado es `index.json` junto al ejecutable (`Search/index.json` en la distribución). Si falta, arranca vacío; una ruta `--index-file` explícita ausente o inválida falla cerrado. El comando de servicio del ejemplo presupone que el índice ya se importó.

El catálogo tiene schemaVersion 1, máximo 1000 documentos y 16 MiB; contenido máximo 64 KiB UTF-8 por documento. La importación valida todo antes de reemplazar el destino atómicamente. El índice se carga como instantánea al arrancar, usa términos Unicode y relevancia BM25 con título ponderado y empate por URL; sin coincidencias devuelve vacío. No hay rastreo, historial de consultas ni caché de resultados. Una URL canónica duplicada, incluso si solo cambia el fragmento, rechaza toda la importación; nunca publica un catálogo parcial. La aceptación Windows física y web general sigue pendiente.

La distribución Windows publica `Optimus.SearchHost.exe` autocontenido en `Search/`, junto al navegador `Optimus.exe` y ambos runtimes. Ver [protocolo](docs/PROTOCOL.md), [guía Windows](https://github.com/Voxterrae/HUB_Optimus/blob/feat/browser-windows-search-2021/products/browser/windows/docs/GUIA_0_3.md), [validación](docs/VALIDATION.md), [revisión IA](docs/AI_GOVERNANCE_REVIEW.md) y [empaquetado](https://github.com/Voxterrae/HUB_Optimus/blob/feat/browser-windows-search-2021/products/browser/windows/tools/release/README.md).

La [validación histórica](docs/VALIDATION.md) conserva el bloqueo observado con los motores upstream de SearXNG. El nuevo [registro del piloto Mwmbl](docs/VALIDATION_MWMBL_PILOT.md) y su [revisión de integración](docs/AI_GOVERNANCE_REVIEW_MWMBL_PILOT.md) separan las pruebas controladas de las consultas reales a través de Optimus. Los fixtures no demuestran resultados de Internet ni ejecución Windows.

El endpoint SearXNG admite HTTPS o HTTP con `localhost` literal o una IP loopback. Conserva un prefijo como `/instance`, `/instance/` o `/instance/search` y solicita `/instance/search`. Si `unresponsive_engines` no está vacío, devuelve un fallo genérico 502, también si hay resultados parciales; una lista vacía sana sigue siendo válida.

## Piloto externo Mwmbl: selección explícita

El operador puede iniciar un host de prueba con esta única selección de proveedor:

```sh
dotnet run --project src/Optimus.Search/Optimus.Search.csproj -c Release -- --port 17831 --token-file /ruta/al/perfil-de-prueba/service.token --web-provider mwmbl
```

La ruta es un marcador para un perfil de prueba propio, fuera del repositorio. No se escribe el token en argumentos. `--web-provider mwmbl` y `--searx-url` son incompatibles; valores de proveedor desconocidos y opciones repetidas se rechazan. Sin ninguno, Web sigue sin configurar; el índice local continúa disponible. El launcher y la configuración nativa existentes conservan su comportamiento: este incremento no activa Mwmbl al abrir el navegador ni actualiza automáticamente una alpha descargada.

Cada búsqueda `scope=web` de ese host envía la consulta por HTTPS a `https://api.mwmbl.org/api/v2/search/?q=...`. El proveedor ve la consulta y la dirección de salida de red; la modalidad sin cuenta no ofrece anonimato de red. No se reenvía el bearer local, ni se añaden claves API, cookies o credenciales HTTP ambientales. No hay redirecciones, reintentos automáticos ni sustitución por SearXNG, Wikipedia o el índice. `scope=index` no consulta ese endpoint.

El adaptador acepta como máximo 1 MiB de JSON con profundidad 32, conserva hasta 20 resultados válidos en el orden recibido y aplica los límites de URL, título y contenido del [protocolo](docs/PROTOCOL.md). Coordina las instancias del mismo proceso con un mínimo de 1,1 s entre inicios externos. El plazo de 10 s incluye esa espera, cabeceras y cuerpo; la cancelación también interrumpe la espera. Esta coordinación no administra la cuota mensual ni el tráfico de otros procesos o equipos que compartan IP. Un 429 externo se devuelve como `429 / upstream-rate-limited`, sin resultados ni reintento automático.

La documentación externa consultada el 01/11/2026 publica acceso anónimo de 1.000 consultas/mes y 1 solicitud/s por IP, sin SLA. Esta opción no registra cuenta, tarjeta ni facturación. Consulte [el acceso publicado](https://developer.mwmbl.org/) y [las condiciones](https://developer.mwmbl.org/terms/) antes de usarla.

Las condiciones permiten aplicaciones comerciales, pero atribuyen a los resultados CC BY-NC-SA 4.0; esa tensión no se resuelve aquí. El alcance es un piloto técnico privado y finito. El despliegue comercial y la reutilización de resultados quedan pendientes de aclaración; no se importan al índice Optimus.

Mwmbl es una fuente externa y su cobertura no es un índice mundial propio de Optimus. El campo `source` conserva la procedencia reconocida del resultado: índice Mwmbl, comunidad, Wikipedia o Google; si no se reconoce, indica origen no especificado. El parámetro local `language` no constituye filtrado por idioma en Mwmbl y no se transmite como filtro externo. No se garantiza SafeSearch, relevancia, actualización, disponibilidad ni cobertura total. La prueba del cliente y de la interfaz en Windows sigue siendo una aceptación separada.
