# Validación Windows / Optimus Search 0.3 alpha — #2021

Fecha UTC: 30 de octubre de 2026. Este registro corresponde al incremento sobre #2018, separado de [la importación histórica 0.2](https://github.com/Voxterrae/HUB_Optimus/blob/79c1d95d65e0f8b903039249cd8ce890b1ffe111/products/browser/VALIDATION.md). El head distribuido, la PR y la decisión humana se registran externamente después del último push; este archivo no intenta incluir su propio SHA.

| Comprobación | Evidencia y límite |
| --- | --- |
| Base de partida | 74 comprobaciones C# y seis Python correctas antes del incremento; evidencia histórica, no acreditación de 0.3. |
| Integración anterior a la revisión final | En 70e1438: 35 Core + 37 Search Windows + 24 Privacy + 28 backend = 124 comprobaciones C#; 13 Python correctas. Compilación WPF sin errores ni advertencias. La revisión posterior detectó problemas adicionales y este resultado no acredita sus correcciones. |
| Correcciones de revisión final | Integración local 78242d7: 35 Core + 47 Search Windows + 24 Privacy + 39 backend = 145 comprobaciones C#; 13 Python correctas. Transporte TLS real positivo, sustitución de listener/reconexión adversaria sin revelar HTTP, cancelación y errores upstream cubiertos. WPF sin errores ni advertencias. La PR registra el SHA público equivalente tras el último push. |
| Publicación Windows x64 | Se han generado apphosts autocontenidos reales para navegador y host con SDK 10.0.403 y runtimes 10.0.14. El paquete definitivo se reconstruye desde el head final y se comprueba estructuralmente; ejecutar un PE en Windows sigue pendiente. |
| Índice propio | El CLI real importó tres documentos originales de Ayuda Optimus. Las pruebas de integración usan servicio y cliente reales contra corpus finitos; no acreditan un índice mundial. |
| Web general | BLOQUEADA: SearXNG oficial instalado y JSON operativo, sin resultados generales relevantes en las consultas controladas. Google denegó acceso, DuckDuckGo pidió CAPTCHA, Brave devolvió 429 y Bing resultados irrelevantes o vacíos. No se eludieron restricciones. |
| Scripts PowerShell | Revisión como fuente; PowerShell no está disponible en el entorno Linux. No ejecutados. |
| Windows físico | Interfaz, teclado, Narrador/NVDA, escala 200 %, alto contraste, WebView2, cookies privadas, limpieza COM y ciclo de procesos pendientes. |
| Firma | Alpha sin firma; no se afirma certificación, merge, despliegue ni aprobación humana. |

Comandos de integración: `dotnet build <proyecto> -c Release -m:1` y `dotnet run --project <proyecto> -c Release --no-build` para `windows/tests/Optimus.{Core,Search,Privacy}.Tests` y `search/tests/Optimus.Search.Tests`; `python -m unittest discover -s products/browser/windows/tools/release -v`; `dotnet build products/browser/windows/src/Optimus.App/Optimus.App.csproj -c Release -p:EnableWindowsTargeting=true -m:1`. SDK oficial 10.0.403 verificado con SHA-512 de sus metadatos oficiales.

Dos invocaciones iniciales de `dotnet run` fallaron durante la compilación/restauración sin diagnóstico útil en este entorno. La compilación serial explícita y ejecución sin recompilar completaron las suites; no se atribuye una causa no demostrada ni se ocultó el intento fallido. La primera importación con ruta relativa falló por el directorio efectivo de `dotnet run`; la ejecución con entradas/salidas absolutas funcionó.

El diff de código pasa `git diff --check` excluyendo únicamente el aviso oficial ASP.NET. La comprobación completa devuelve 13 líneas con espacios finales dentro de ese archivo; se conservan para mantener idénticos los bytes oficiales y su SHA-256, sin cambiar checks o configuración de Git.

Las pruebas Python usan Git temporal y PE sintéticos que nunca se ejecutan. La entrega final usa los apphosts publicados reales; comprueba AMD64, runtimes autocontenidos, avisos, corpus requerido, CRC y cobertura SHA-256 completa. Estos controles no sustituyen la prueba del navegador instalado.

El manifiesto histórico `products/browser/SOURCE_MANIFEST.json` permanece intacto. El manifiesto nuevo de fuentes y el registro externo describen 0.3. El ZIP conserva las referencias de proyecto mediante `Source/Windows/` y `Source/Search/`; no contiene perfiles, token, certificados privados, SDK, entorno SearXNG de QA ni documentos privados.

No se han creado cuentas/proveedores de pago ni activado Azure, Dataverse, IA, IoT o permisos como parte de este incremento. El certificado efímero tiene validez de 30 días desde el arranque: un host independiente que permanezca abierto más tiempo debe reiniciarse para renovarlo; el vencimiento rechaza conexiones. Las decisiones técnicas y sus costes se registran en [DECISIONS.md](https://github.com/Voxterrae/HUB_Optimus/blob/feat/browser-windows-search-2021/products/browser/search/docs/DECISIONS.md). El siguiente hito de producto es una consulta web relevante con proveedor operativo y la aceptación en Windows físico; ambos siguen separados de la validación de código.
