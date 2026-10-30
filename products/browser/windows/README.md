> **Arranque y diagnóstico 0.3.2 — 30/10/2026:** corrección del plazo de arranque en frío y diagnóstico Windows autocontenido. [Guía 0.3.2](docs/GUIA_0_3_2.md). La ejecución real de servicio/interfaz en Windows sigue pendiente; la propuesta CI está inactiva.

> **Diseño nativo 0.3.1 — 30/10/2026:** el ejecutable incorpora la identidad visual, el inicio con buscador, las tarjetas y los paneles adaptables. [Guía 0.3.1](docs/GUIA_0_3_1.md). El comportamiento del servicio de búsqueda 0.3 se conserva; la aceptación Windows/accesibilidad sigue pendiente.

# Optimus Windows 0.3 alpha — búsqueda compartida

WPF/WebView2 con servicio local .NET 10 en `../search`. Web es la fuente predeterminada mediante ese servicio; Índice Optimus consulta un catálogo finito offline y Wikipedia es una elección explícita. El SearXNG web lo configura el operador. Alpha sin firma; ejecución y accesibilidad de esta versión en Windows pendientes.

Lee [GUIA_0_3.md](docs/GUIA_0_3.md) para uso, token, configuración y límites, [el protocolo](../search/docs/PROTOCOL.md) y [la validación 0.3](../search/docs/VALIDATION.md). La guía local funciona mediante reglas; no hay asistente generativo conectado, voz ni IoT.

## Compilar y comprobar

Desde este directorio, con SDK .NET 10.0.403 (`global.json`):

```sh
dotnet run --project tests/Optimus.Core.Tests -c Release
dotnet run --project tests/Optimus.Search.Tests -c Release
dotnet run --project tests/Optimus.Privacy.Tests -c Release
dotnet run --project ../search/tests/Optimus.Search.Tests -c Release
python3 -m unittest discover -s tools/release -v
dotnet build Optimus.slnx -c Release -p:EnableWindowsTargeting=true -m:1
```

Publicación autocontenida Windows x64 del navegador, servicio y diagnóstico, sin ejecutarlos:

```sh
dotnet publish src/Optimus.App/Optimus.App.csproj -c Release -r win-x64 --self-contained true -p:EnableWindowsTargeting=true -m:1 -o artifacts/win-x64
dotnet publish ../search/src/Optimus.Search/Optimus.Search.csproj -c Release -r win-x64 --self-contained true -p:Version=0.3.2-alpha -m:1 -o artifacts/win-x64/Search
dotnet publish scripts/WindowsSmoke/Optimus.Windows.Smoke.csproj -c Release -r win-x64 --self-contained true -p:EnableWindowsTargeting=true -m:1 -o artifacts/win-x64/Diagnostics
```

Después hay que copiar ayuda y avisos exactamente como describe [el empaquetador](tools/release/README.md), y comprobar la publicación antes de generar el ZIP. Los scripts PowerShell `scripts/Build-Optimus.ps1` y `scripts/Verify-Optimus.ps1` automatizan tests, publicación/compilación y comprobaciones. `Build` requiere Python y copia documentación y avisos de terceros; los tres ejecutables son autocontenidos. Los scripts no se han ejecutado en el entorno Linux sin PowerShell.

.NET/WPF/ASP.NET Core se distribuyen con avisos de terceros. WebView2 Evergreen se necesita por separado en Windows. Ningún comando de compilación instala el producto, firma ejecutables o acredita accesibilidad.

## Procedencia

[SOURCE_MANIFEST.json](../SOURCE_MANIFEST.json) y [VALIDATION.md](../VALIDATION.md) son registros históricos de la importación 0.2: sus hashes no describen los archivos modificados para 0.3. El [registro 0.3](../search/docs/VALIDATION.md) recoge el estado del incremento; el integrador generará hashes finales nuevos después de ensamblar los commits. El nuevo ZIP conserva `Source/Windows/` y `Source/Search/` como hermanos para reproducir las referencias relativas. No modifica el ZIP original ni sus hashes.
