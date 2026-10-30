# Optimus Windows 0.2 alpha — snapshot de fuentes

Navegador nativo WPF con WebView2. Esta incorporación conserva el código del artefacto 0.2 sin cambiar su comportamiento. Es una alpha sin firma; la validación de esta versión ejecutándose en Windows sigue pendiente.

Incluye navegación con pestañas, marcadores, permisos explícitos, reglas locales de bloqueo o apertura privada, perfiles privados, guía local y una búsqueda limitada mediante Wikipedia/marcadores, con SearXNG opcional configurado por el operador. El asistente generativo remoto, idiomas adicionales, voz y dispositivos IoT no están conectados.

## Compilación y pruebas

Trabajar desde este directorio. El SDK está fijado en `global.json` a .NET 10.0.403 con actualización de parche permitida. La aplicación requiere Windows x64 y WebView2 Evergreen para ejecutarse.

```sh
dotnet run --project tests/Optimus.Core.Tests -c Release
dotnet run --project tests/Optimus.Search.Tests -c Release
dotnet run --project tests/Optimus.Privacy.Tests -c Release
dotnet build Optimus.slnx -c Release -p:EnableWindowsTargeting=true -m:1
python3 -m unittest discover -s tools/release -v
```

Publicación autocontenida, sin ejecutar el producto:

```sh
dotnet publish src/Optimus.App/Optimus.App.csproj -c Release -r win-x64 --self-contained true -p:EnableWindowsTargeting=true -m:1 -o artifacts/win-x64
```

Los scripts PowerShell originales producen, en cambio, una publicación dependiente del runtime de escritorio instalado. No debe confundirse esa salida con la entrega ZIP 0.2 autocontenida. Sus comandos no se han ejecutado en esta importación.

Limitación heredada del script: copia `PILOTO.md` pero omite la guía enlazada `GUIA_0_2.md`. Si se distribuye esa salida, hay que incluir también la guía; desde este directorio:

```powershell
Copy-Item docs/GUIA_0_2.md artifacts/win-x64/GUIA_0_2.md
```

La utilidad `tools/release/package_optimus.py` empaqueta una publicación ya construida; requiere metadatos verdaderos de una entrega nueva. No instala ni firma la aplicación.

Consulta [la guía 0.2](docs/GUIA_0_2.md), [el piloto](docs/PILOTO.md), [la validación de la importación](../VALIDATION.md) y [la procedencia](../SOURCE_MANIFEST.json). Los avisos de terceros permanecen en `docs/third-party/`.
