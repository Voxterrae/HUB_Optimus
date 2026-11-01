# Validación del piloto Web Mwmbl — #2021

Fecha del registro: 01/11/2026. Registro de pruebas controladas y tres consultas reales en Linux. La aceptación de Windows, la integración para usuarios y el despliegue comercial siguen pendientes.

## Referencia y alcance

Base final: `46085be8dec5676271290eb3e2906546fc7efd77` (#2034), incorporando su corrección del descubrimiento del host de pruebas y cierre por EOF. Head público final y PR se registran fuera de este documento en #2021 para evitar un SHA autorreferente. Revisión independiente del incremento completo: sin hallazgos Critical/Important ni defectos menores que requieran corrección; revisión técnica asistida, no aprobación humana. Diseño: [piloto explícito](superpowers/specs/2026-11-01-mwmbl-pilot-design.md); plan: [implementación](superpowers/plans/2026-11-01-mwmbl-pilot.md).

El incremento añade `--web-provider mwmbl` al host .NET 10 existente, mutuamente excluyente con `--searx-url`, y un mensaje específico para cuota en el cliente. La selección es explícita: no cambia el inicio automático nativo ni convierte una alpha ya distribuida en un cliente nuevo. Conserva protocolo v1, TLS/HMAC/SPKI, nonce, bearer local, Origin/Host, importación e índice sin red. SearXNG conserva el rechazo de respuestas con motores no disponibles, incluso si contienen resultados parciales.

Mwmbl recibe consultas Web y la IP de salida; el bearer del perfil permanece local. No hay nuevas claves, cuentas, tarjetas, facturación, recursos alojados, activación de CI ni fusión en este alcance. Se trata de una prueba técnica privada y finita de una fuente externa, sin crear un corpus con sus resultados ni importarlos al índice.

## Condiciones externas revisadas

La documentación publicada consultada el 01/11/2026 anuncia modalidad anónima de 1.000 consultas/mes, 1/s por IP y sin SLA. La portada anuncia uso sin registro; las condiciones también contienen una formulación general que exige cuenta/clave. Se conserva esa discrepancia como límite documental, sin inventar una autorización.

Las condiciones permiten aplicaciones comerciales y simultáneamente sitúan los resultados bajo CC BY-NC-SA 4.0 y derechos de origen. No se concluye que el permiso de acceso elimine esas restricciones. El despliegue comercial y la reutilización de resultados quedan **BLOQUEADOS hasta aclaración**. Este registro no cambia licencias, titularidad ni derechos de terceros.

Fuentes primarias:

- [Acceso y cuotas publicados](https://developer.mwmbl.org/).
- [Condiciones de API, uso y resultados](https://developer.mwmbl.org/terms/).
- [Contrato de la API v2 en fuente oficial](https://github.com/mwmbl/mwmbl/blob/main/mwmbl/tinysearchengine/search.py).
- [Límites del motor documentados por SearXNG](https://docs.searxng.org/dev/engines/online/mwmbl.html).

El espaciado de 1,1 s del proceso es una protección local, no una reserva de cuota ni coordinación entre equipos. No se intenta evadir respuestas 429 o bloqueos. No se afirma filtrado por idioma, SafeSearch, relevancia, cobertura total o disponibilidad estable.

## Pruebas controladas

Entorno: Ubuntu 24.04.3 LTS, SDK .NET 10.0.403, runtime 10.0.14. Los dobles HTTP sirven para comprobar comportamiento; no son evidencia de Internet. Baseline limpio inicial c929bfe: Core 39, Search Windows 59, Privacy 24, backend 46, Python 21, seis compilaciones sin avisos/errores. La actualización al padre 46085be8 cambia pruebas y documentación; no cambia producción frente a c929bfe.

| Comprobación | Evidencia final |
| --- | --- |
| CLI nueva: RED contra base y GREEN; rechazo de proveedor inválido, opciones repetidas y combinación con SearXNG | RED 46/47 por rechazo del nuevo argumento; GREEN 47/47 inicial con selección explícita y cierre EOF. Negativos y ejecución sin DOTNET_ROOT incluidos en regresión final. |
| JSON válido/vacío, esquema/error, filas inválidas, URLs y duplicados, límites y procedencia reconocida/no especificada | RED del adaptador 47/56; GREEN inicial 56/56. Se comprueban respuestas reales del parser sobre fixtures, no listas prefabricadas devueltas por el adaptador. |
| Rechazo de redirección/estado externo; 429 genérico sin fallback ni reintento | Casos 301/403/429/500 y API HTTPS real con upstream controlado; una sola llamada y sin detalle del cuerpo externo. |
| 1 MiB, profundidad 32 y plazo total 10 s | Límite declarado y lectura máxima 1 MiB + 1; profundidad 32; deadline de cabeceras y cuerpo bloqueado en regresión final. |
| Cancelación y espaciado mínimo 1,1 s | Cancelación durante cuerpo libera stream; espera cancelada no despacha; separación observada entre dos instancias bajo reloj monotónico. |
| Bearer, cookies y credenciales externas | Fixture verifica ausencia de Authorization/Cookie. Construcción del handler desactiva cookies, credenciales y redirecciones; no se suministran secretos externos. |
| Mensaje nativo de cuota | RED 59/60 con fallo exclusivo del nuevo caso tras compilación correcta; GREEN 60/60 en regresión final. La respuesta 429 muestra límite de consultas y no expone el cuerpo privado del proveedor. |
| Regresión final | Core 39/39, cliente Search 60/60, Privacy 24/24, backend 59/59: 182 comprobaciones C# portables; Python 21/21. |
| Compilaciones | Seis builds Release con 0 avisos/errores, incluidos WPF y helper con EnableWindowsTargeting. |
| Revisión independiente del incremento | Los 16 archivos y contexto revisados; sin hallazgos Critical/Important/Minor que requieran corrección. No acredita merge, despliegue o aceptación humana. |

Comandos finales, desde `products/browser/windows`, con SDK .NET en `PATH` y configuración Release:

```sh
dotnet build tests/Optimus.Core.Tests -c Release -m:1
dotnet run --project tests/Optimus.Core.Tests -c Release --no-build
dotnet build tests/Optimus.Search.Tests -c Release -m:1
dotnet run --project tests/Optimus.Search.Tests -c Release --no-build
dotnet build tests/Optimus.Privacy.Tests -c Release -m:1
dotnet run --project tests/Optimus.Privacy.Tests -c Release --no-build
python3 -m unittest discover -s tools/release -v
dotnet build src/Optimus.App -c Release -m:1 -p:EnableWindowsTargeting=true
dotnet build scripts/WindowsSmoke/Optimus.Windows.Smoke.csproj -c Release -m:1 -p:EnableWindowsTargeting=true
```

Desde `products/browser/search`: `dotnet build tests/Optimus.Search.Tests -c Release -m:1` y `dotnet run --project tests/Optimus.Search.Tests -c Release --no-build`.

Un primer intento final del backend dio 58/59 al quitar DOTNET_ROOT en su prueba de descubrimiento: el SDK temporal no estaba en PATH. Se conservó ese resultado y se corrigió el entorno incluyendo la ruta del SDK. La misma suite pasó 59/59 sin cambiar código. La prueba del CLI piloto reutiliza el descubrimiento del padre y elimina DOTNET_ROOT del entorno del hijo. La variante completa ejecutada por DLL con DOTNET_ROOT ausente y SDK en PATH pasó también 59/59; es cobertura repetida, no 59 casos adicionales. Los 74 inputs de compilación coinciden antes/después de las 12 ejecuciones finales. SHA256 del manifiesto de inputs: `586b7ebf91a449c352364069aacb4d6f3682c13beb52327e0f7fea737d74c0ba`.

Observación de cobertura de la revisión: se prueba cancelación durante el espaciado y durante el cuerpo, pero no un segundo solicitante cancelado mientras otro conserva el semáforo. La espera usa el mismo token/deadline en código; se acepta esa ausencia como límite de regresión del borrador, sin afirmar que se probó ese escenario.

## Consultas reales de extremo a extremo

La aceptación de esta ruta exige usar el **cliente TLS de producción → host Optimus real → adaptador Mwmbl → API externa**. Una consulta directa al proveedor no acredita esa cadena. No se registran bearer, claves privadas o datos de perfiles. Registrar consultas públicas benignas, momento UTC, plataforma, referencia del código, tiempos, HTTP, cantidad de resultados y destinos comprobados; separar resultados vacíos, rechazos y errores de los satisfactorios. La respuesta debe identificar su procedencia externa.

| Consulta | Momento y tiempo | HTTP / resultados / fuente | Resultado final |
| --- | --- | --- | --- |
| `web accessibility` | 17:07:15Z · 5438 ms | 200 / 20 / Mwmbl índice | Incluye `https://web.dev/accessibility/`. |
| `accesibilidad web` | 17:07:16Z · 244 ms | 200 / 20 / Mwmbl índice | Incluye `https://web.dev/articles/color-and-contrast-accessibility?hl=es`. |
| `linux` | 17:07:18Z · 364 ms | 200 / 20 / 1 comunidad + 19 índice | Incluye `https://www.linux.org/`. |

Ejecutadas el 01/11/2026 en Ubuntu 24.04.3. `LocalSearchTransport.CreateClient(token)` de producción autenticó TLS mediante la prueba HMAC ligada al SPKI/puerto. Se usaron `SearchServer.StartAsync`, un índice vacío y `MwmblSearchProvider` reales; GET local autenticado `/search?format=json&q=...&scope=web&language=es`. Metadata: versión 1, Web configurada, 0 documentos importados. Sin desactivar TLS, instalar certificados, cambiar proxy/CA ni enviar el bearer fuera del loopback. El host se cerró al terminar: no queda un servicio permanente.

La prueba se ejecutó sobre c929bfe más la implementación del adaptador; la posterior actualización a 46085be8 solo cambia pruebas/documentación del padre. No se modificó la implementación de producción entre la consulta y la regresión final. El primer arnés falló después de recibir una respuesta al leer un campo inexistente `meta` en vez del real `optimus`; se corrigió el arnés y se hicieron las tres consultas explícitas registradas. Aquella ejecución fallida no se cuenta como aceptación.

Los destinos de la tabla son URLs devueltas, no páginas visitadas o certificadas como seguras. No se publica ni importa un dataset de resultados. Esto demuestra tránsito real de la consulta, no relevancia excelente: `linux` también incluyó una página de carrito de compra. Hace falta evaluar calidad y cobertura con personas y consultas representativas antes de recomendar uso diario.

Confirmar que `scope=index` mantiene el corpus finito y no accede a Mwmbl; no cambiar automáticamente de proveedor cuando Web falle. Una cuota agotada no se resuelve con resultados fijos ni con consultas desde otra identidad o red.

## Límites de aceptación y siguiente paso

- **Windows nativo y GUI:** pendientes de prueba específica de estas fuentes; una ejecución de .NET/Linux no acredita WPF, WebView2, accesibilidad ni el servicio empaquetado en Windows.
- **Integración para usuarios:** la opción CLI requiere un host seleccionado expresamente; este incremento no ofrece una instalación automática, una nueva descarga Windows, un servicio permanente ni integración web pública.
- **Cobertura:** resultados de Mwmbl y su procedencia externa no constituyen un índice mundial propio de Optimus. El índice propio de ayuda conserva su alcance finito.
- **Operación comercial y reutilización:** bloqueadas por la ambigüedad documental indicada; no inferirlas de una respuesta 200.

La PR y #2021 registran el SHA final y los límites conservados. Las tres consultas acreditan este piloto del servicio; la aceptación de cada plataforma sigue separada. No se modifican los registros históricos de [validación 0.3](VALIDATION.md) ni los manifiestos anteriores.
