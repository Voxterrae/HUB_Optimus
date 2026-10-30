# Empaquetador Optimus Browser 0.3.0 alpha

Python 3.9+ de biblioteca estándar y `git` en PATH. Empaqueta una publicación ya compilada; no ejecuta, instala ni firma el producto. El ZIP original 0.2 y su manifest de importación permanecen como evidencia histórica.

Desde `products/browser/windows`:

```sh
python3 tools/release/package_optimus.py \
  --source-root "$PWD" \
  --search-source-root "$PWD/../search" \
  --binary-root /ruta/a/publish-win-x64 \
  --output-dir /ruta/a/entrega \
  --metadata /ruta/a/metadata.json
```

Ambas raíces de fuentes son obligatorias y pueden ser subdirectorios de un único repositorio Git. `git ls-files --cached` determina sus nombres; se leen los bytes actuales del árbol de trabajo, no los de un commit declarado. Revisar el estado Git y registrar diferencias intencionadas antes de distribuir. Los IDs de metadatos no certifican por sí solos un árbol limpio.

La salida debe estar fuera de todas las entradas. El éxito devuelve 0; validación fallida 1 y argumentos inválidos 2. Primero crea/verifica un ZIP temporal; un rechazo no reemplaza una entrega anterior. Produce:

- `Optimus_Browser_Windows_0.3.0_alpha.zip`
- `Optimus_Browser_Windows_0.3.0_alpha.zip.sha256`

## Layout congelado de esta entrega

Todo queda bajo `Optimus_Browser_0.3.0_alpha/`:

| Ruta | Contenido |
| --- | --- |
| `Optimus.exe`, `Optimus.dll`, runtime | Navegador nativo autocontenido Windows x64. |
| `Search/Optimus.SearchHost.exe`, DLL y runtime | Servicio separado autocontenido Windows x64. |
| `Search/index.json` | Tres ayudas públicas, importadas por el CLI real desde Source/Search/catalog/optimus-help.json. Corpus finito, no resultados web. |
| `Source/Windows/` | Archivos Git seleccionados del módulo Windows. |
| `Source/Search/` | Archivos Git seleccionados del módulo Search. |
| `GUIA_0_3.md`, `Search/README.md`, `Search/docs/` | Ayuda, protocolo, evidencia y revisión IA. |
| `third-party/` | Avisos originales .NET, WPF, WebView2 y avisos oficiales ASP.NET Core. |
| `LEEME.txt`, `VALIDACION.md`, `DECISIONES.md` | Uso, evidencias declaradas y decisiones generadas. |
| `SHA256SUMS.txt` | Todos los demás archivos interiores, ordenados por ruta. |

La estructura `Source/Windows` y `Source/Search` es nueva respecto a `Source/` de 0.2; conserva las referencias relativas entre proyectos. No se presenta como identidad de bytes con el ZIP 0.2. El integrador debe generar un manifest 0.3 nuevo de las fuentes finales; nunca reescribir los hashes originales como si describieran archivos modificados.

## Preparar publicación

`../../scripts/Build-Optimus.ps1` automatiza estos pasos desde Windows con PowerShell y Python. Desde Linux se pueden publicar ambos apphosts sin ejecutarlos:

```sh
dotnet publish src/Optimus.App/Optimus.App.csproj -c Release -r win-x64 --self-contained true -p:EnableWindowsTargeting=true -m:1 -o /ruta/a/publish-win-x64
dotnet publish ../search/src/Optimus.Search/Optimus.Search.csproj -c Release -r win-x64 --self-contained true -p:Version=0.3.0-alpha -m:1 -o /ruta/a/publish-win-x64/Search
```

Después importar la ayuda con el host ejecutado desde fuentes (no ejecutar un PE Windows en Linux):

```sh
dotnet run --project ../search/src/Optimus.Search/Optimus.Search.csproj -c Release -- index --input "$PWD/../search/catalog/optimus-help.json" --output /ruta/a/publish-win-x64/Search/index.json
```

Después copiar `docs/GUIA_0_3.md` al raíz de publicación, `docs/third-party/` como `third-party/`, `../search/README.md` a `Search/README.md` y los documentos Search `PROTOCOL.md`, `VALIDATION.md`, `AI_GOVERNANCE_REVIEW.md` a `Search/docs/`. Puede incluirse `PILOTO.md` como lista histórica, sin presentarlo como aceptación 0.3. No copiar directorios de perfiles, tokens, catálogos privados, logs, informes QA ni herramientas de compilación.

```sh
python3 tools/release/package_optimus.py --verify-publication /ruta/a/publish-win-x64
```

Esta comprobación independiente valida archivos, apphosts y runtimes sin metadatos ni repositorios. No prueba su ejecución. `BUILD-SHA256SUMS.txt` es el manifest de la publicación PowerShell; tiene nombre distinto del `SHA256SUMS.txt` final para evitar colisiones. `Verify-Optimus.ps1` exige cobertura completa del manifest de publicación y vuelve a ejecutar suites y compilaciones; no lanza el producto Windows.

## Metadatos

Objeto JSON UTF-8; todas estas cadenas son obligatorias y no vacías. Campos extra se ignoran; no se copia el JSON original.

| Campo | Contenido |
| --- | --- |
| `source_commit` | ID Git hexadecimal completo de 40/64 caracteres para Windows. |
| `search_source_commit` | ID Git completo para Search; puede ser el mismo en el monorepo. |
| `native_tests` | Comandos/resultados nativos realmente ejecutados y límites. |
| `search_tests` | Comandos/resultados del servicio realmente ejecutados y límites. |
| `companion_tests` | Evidencia real del acompañante externo, o estado pendiente explícito. |
| `companion_url` | URL HTTPS del repositorio/referencia externa del acompañante. |
| `plugin_id` | Identificador real si se incluye un plugin; si esta entrega nativa no incluye ninguno, declarar explícitamente `No se incluye plugin de ChatGPT`. Nunca inventar un ID. |
| `validation` | Fecha/plataforma, evidencia, diferencias intencionadas y comprobaciones pendientes. |
| `decisions` | Decisiones de esta entrega. |

El operador debe aportar evidencia verdadera. El empaquetador no comprueba que los comandos declarados se ejecutaran ni que el plugin o la URL existan. No inventar IDs, tests, aceptación Windows ni resultados web. Una fixture no es evidencia general de Internet.

## Rechazos e integridad

- Exige apphosts `Optimus.exe` y `Search/Optimus.SearchHost.exe` con firma PE AMD64. Exige DLL, deps.json y runtimeconfig de ambos, coreclr/hostpolicy/System.Private.CoreLib en ambos directorios, PresentationFramework, WebView2 Core y ensamblados ASP.NET/Kestrel. No impone AMD64 a ensamblados administrados AnyCPU.
- Ambos runtimeconfig deben declarar .NET 10 autocontenido mediante includedFrameworks: NETCore más WindowsDesktop o ASP.NET Core según el ejecutable; rechaza framework/frameworks dependientes de runtime instalado. Es una comprobación estructural mínima, no certificación funcional del runtime completo.
- Exige guía, documentación Search y los siete avisos .NET/WPF/WebView2/ASP.NET. Los avisos ASP.NET comprometidos son bytes oficiales v10.0.14; Build y el empaquetador fallan si el host publicado usa otra versión hasta actualizar avisos/procedencia y la validación de versión. Ver [procedencia](../../docs/third-party/ASPNetCore.PROVENANCE.md).
- Solo selecciona nombres Git de ambas fuentes; omite `.git`, `.superpowers`, bin, obj, artifacts, tooling, __pycache__, .pytest_cache, QA y TestResults. En la publicación rechaza esos directorios en vez de omitirlos. No incorpora el gateway externo.
- Rechaza archivos vacíos, symlinks en cualquier componente, traversal, rutas absolutas/incompatibles con Windows, colisiones sin distinción de mayúsculas y entradas binarias que intenten reemplazar documentos generados o Source/.
- Rechaza perfiles y datos de navegador, credenciales, service.token, claves/certificados privados y `.env` (salvo `.env.example` versionado y escaneado). Escanea entradas y metadatos con patrones de secretos UTF-8/UTF-16 sin mostrar coincidencias. Es una barrera adicional; no sustituye revisión humana de privacidad.
- Verifica CRC, rutas y cobertura/hash completos antes de entregar. Fija fechas, permisos y orden ZIP. Mismos bytes y misma versión Python/zlib producen el mismo ZIP; no promete igualdad entre compresores distintos.

## Pruebas

```sh
python3 -m unittest discover -s tools/release -v
```

Repositorios Git temporales y PE sintéticos no ejecutables ejercitan la CLI real, selección de dos fuentes, rechazo de host/runtime/avisos/documentación ausentes, privacidad, arquitectura, reproducibilidad e integridad. Nunca se ejecutan los PE sintéticos.
