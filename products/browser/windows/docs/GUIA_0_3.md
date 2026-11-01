# Optimus Windows 0.3 alpha — búsqueda local y web

Incremento de #2021 sobre la importación 0.2 de #2018. Alpha privada sin firma. Requiere Windows x64 y Microsoft Edge WebView2 Evergreen Runtime. La entrega incluye .NET 10, Windows Desktop y ASP.NET Core; conserva `Search/` junto a `Optimus.exe` al descomprimir. No instala servicios ni cambia el navegador predeterminado.

## Elegir la fuente

- **Web** usa el servicio local Optimus con un SearXNG controlado y configurado por el operador. Sin esa configuración informa el problema; no cambia a Wikipedia.
- **Índice Optimus** consulta offline solo los documentos importados explícitamente. La entrega incluye tres documentos breves de Ayuda Optimus para probarlo con «servicio local» o «importar documentos». Un resultado vacío puede significar que el catálogo no cubre esa consulta. No es un índice de toda la web.
- **Wikipedia** realiza esa búsqueda únicamente cuando se elige expresamente.

Buscar e Intro respetan la fuente elegida en el formulario. Una búsqueda de texto desde la barra de direcciones selecciona Web explícitamente. Escribir o cambiar fuente invalida una búsqueda anterior y no envía una nueva automáticamente. Los marcadores locales conservan su alcance y las pestañas privadas no los consultan ni persisten consultas/resultados.

## Servicio local

La aplicación puede iniciar únicamente `Search/Optimus.SearchHost.exe` de su propia carpeta. El servicio escucha en `https://127.0.0.1:17831`; no se publica en la red. La aplicación termina solo el proceso que inició. Un servicio independiente sigue bajo control de su operador y cambiar su configuración requiere reiniciarlo por separado.

Para operar el host por separado desde PowerShell, usando rutas del perfil del usuario:

```powershell
$searchProfile = Join-Path $env:LOCALAPPDATA 'Optimus/Search'
New-Item -ItemType Directory -Force $searchProfile | Out-Null
.\Search\Optimus.SearchHost.exe --port 17831 --searx-url https://searx.example.org
```

`https://searx.example.org` es un marcador que el operador debe sustituir por su instancia controlada; no es un proveedor configurado ni una prueba de acceso. Solo se admiten HTTPS o HTTP con localhost literal o IP loopback, sin credenciales, query ni fragmento. Se conserva el prefijo de la instancia, por ejemplo `/instance/search`. No se utiliza una instancia pública aleatoria. La búsqueda web puede fallar por restricciones de los motores aunque SearXNG esté instalado correctamente. Si algún motor informa un fallo, se muestra un error genérico, incluso si hay resultados parciales; no se cambia de proveedor.

Sin `--index-file`, el host busca `Search/index.json` junto a su ejecutable. Build genera ese archivo mediante la importación real de `Source/Search/catalog/optimus-help.json` (tres ayudas públicas de Optimus); si falta, arranca con índice vacío. Una ruta explícita ausente o inválida falla cerrado.

El servicio crea un token aleatorio de 32 bytes (exactamente 64 caracteres ASCII hexadecimales sin salto de línea) en `%LOCALAPPDATA%/Optimus/Search/service.token`. Un token existente inválido falla cerrado. La aplicación autentica la clave TLS del servicio mediante ese token antes de enviar cada consulta y Authorization, incluso si cambia la conexión. El certificado temporal permanece en memoria y no modifica la confianza del sistema. El token se envía solo al servicio local en Authorization; nunca a SearXNG. No se copia a settings, argumentos, logs, Git ni al ZIP. El perfil es controlado por el usuario/administrador local; esto no protege contra un proceso comprometido del mismo usuario ni contra administradores.

## Importar un índice finito

Prepara un catálogo JSON público o autorizado fuera de la carpeta de entrega:

```json
{"schemaVersion":1,"documents":[{"url":"https://example.org/ayuda","title":"Ayuda de ejemplo","content":"Texto autorizado para búsqueda local.","source":"Catálogo de ejemplo","updatedUtc":"2026-10-30T00:00:00Z"}]}
```

Es solo un ejemplo de formato, no una búsqueda web ni evidencia de cobertura. Importa y reinicia el servicio con ese índice:

```powershell
.\Search\Optimus.SearchHost.exe index --input C:\Catalogos\catalog.json --output (Join-Path $searchProfile 'index.json')
.\Search\Optimus.SearchHost.exe --index-file (Join-Path $searchProfile 'index.json')
```

La importación acepta como máximo 1000 documentos, 64 KiB UTF-8 de contenido por documento y 16 MiB de archivo. Valida esquema, URL HTTP(S), título y fecha UTC, y publica el catálogo de forma atómica; una entrada inválida no crea un índice parcial. Una URI canónica duplicada, incluso con fragmento distinto, rechaza toda la importación. Al arrancar construye un índice real de términos Unicode con BM25, ponderación de título y desempate por URL. Sin coincidencias devuelve vacío. No rastrea, aprende consultas, registra historial ni guarda resultados.

## Comprobaciones y límites

Comprueba el hash externo del ZIP antes de abrirlo; `SHA256SUMS.txt` cubre los archivos interiores. `VALIDACION.md` declara los comandos efectivamente ejecutados. La estructura PE y los tests no acreditan ejecución Windows.

La aceptación de interfaz, teclado, Narrador/NVDA, escala 200 %, alto contraste, privacidad con WebView2 y limpieza COM debe realizarse en Windows físico con la lista de `PILOTO.md`; ese documento 0.2 es histórico y no acredita la 0.3. Firma, voz, idiomas adicionales, IoT y asistente generativo conectado siguen fuera de esta entrega.

El intento controlado con SearXNG no consiguió resultados web generales relevantes: Google denegó acceso, DuckDuckGo mostró CAPTCHA, Brave devolvió 429 y Bing dio resultados irrelevantes o vacíos. La aceptación web real está bloqueada. Las respuestas de fixtures son pruebas de contrato, nunca aceptación web.
