# Optimus Search — host local compartido v1

Servicio .NET/ASP.NET Core 10 para Web mediante un SearXNG controlado y para un índice propio finito sin conexión. Forma parte del incremento Windows 0.3 alpha de #2021 y mantiene un protocolo reutilizable por Linux, sin modificar su trabajo. No crea cuentas, servicios de pago, Azure, Dataverse ni proveedores de IA.

```sh
dotnet run --project tests/Optimus.Search.Tests -c Release
dotnet run --project src/Optimus.Search/Optimus.Search.csproj -- --port 17831 --index-file /ruta/al/perfil/index.json --searx-url https://searx.example.org
dotnet run --project src/Optimus.Search/Optimus.Search.csproj -- index --input /ruta/catalog.json --output /ruta/al/perfil/index.json
```

La URL es un marcador que el operador sustituye por su instancia controlada. Los caminos de perfil están fuera del código y de los artefactos. Nunca se pasa el valor del token en argumentos. `--token-file` cambia la ruta del archivo de perfil; no acepta un token en texto. El predeterminado está en LocalApplicationData/Optimus/Search/service.token. El servicio usa exclusivamente HTTPS. Windows autentica la clave pública TLS mediante HMAC del token de perfil en cada conexión antes de enviar bearer o consulta; la prueba adicional de health no sustituye esa autenticación. Certificado y clave efímeros solo en memoria, sin cambios al almacén de confianza. `--port 0` permite un puerto efímero en pruebas; siempre IPv4 loopback.

`catalog/optimus-help.json` contiene tres documentos breves redactados para esta entrega y etiquetados Ayuda Optimus. Build los importa mediante el CLI real al publicar: permiten probar «servicio local» o «importar documentos» sin configurar un catálogo propio. No son resultados web; las URLs señalan los documentos de la rama de entrega y las fechas identifican la versión de contenido, sin afirmar una descarga o verificación remota.

El índice predeterminado es `index.json` junto al ejecutable (`Search/index.json` en la distribución). Si falta, arranca vacío; una ruta `--index-file` explícita ausente o inválida falla cerrado. El comando de servicio del ejemplo presupone que el índice ya se importó.

El catálogo tiene schemaVersion 1, máximo 1000 documentos y 16 MiB; contenido máximo 64 KiB UTF-8 por documento. La importación valida todo antes de reemplazar el destino atómicamente. El índice se carga como instantánea al arrancar, usa términos Unicode y relevancia BM25 con título ponderado y empate por URL; sin coincidencias devuelve vacío. No hay rastreo, historial de consultas ni caché de resultados. Una URL canónica duplicada, incluso si solo cambia el fragmento, rechaza toda la importación; nunca publica un catálogo parcial. La aceptación Windows física y web general sigue pendiente.

La distribución Windows publica `Optimus.SearchHost.exe` autocontenido en `Search/`, junto al navegador `Optimus.exe` y ambos runtimes. Ver [protocolo](docs/PROTOCOL.md), [guía Windows](https://github.com/Voxterrae/HUB_Optimus/blob/feat/browser-windows-search-2021/products/browser/windows/docs/GUIA_0_3.md), [validación](docs/VALIDATION.md), [revisión IA](docs/AI_GOVERNANCE_REVIEW.md) y [empaquetado](https://github.com/Voxterrae/HUB_Optimus/blob/feat/browser-windows-search-2021/products/browser/windows/tools/release/README.md).

La aceptación web general real está bloqueada por motores upstream. Los fixtures prueban el protocolo y los límites; no demuestran resultados de Internet ni ejecución Windows.

El endpoint SearXNG admite HTTPS o HTTP con `localhost` literal o una IP loopback. Conserva un prefijo como `/instance`, `/instance/` o `/instance/search` y solicita `/instance/search`. Si `unresponsive_engines` no está vacío, devuelve un fallo genérico 502, también si hay resultados parciales; una lista vacía sana sigue siendo válida.
