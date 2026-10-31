# Validación de apariencia Windows 0.3.3

Fecha: 31/10/2026, UTC. Base pública `f8bbc2faffbd6141de7706e669753c5421f6ae23` (#2026); coordinación #2021. Esta evidencia corresponde a fuentes y ejecución portable en Linux x64. El SHA público final y los hashes de una entrega binaria se registran por separado en la PR y el comentario de entrega, sin identificadores autorreferentes.

## Baseline y regresiones

Antes de cambiar las fuentes se ejecutó un baseline limpio de la base pública: Core 35/35, Search Windows 50/50, Privacy 24/24, backend Search 44/44 y empaquetador 21/21. Las seis compilaciones seriales, incluidas WPF y diagnóstico, terminaron con cero advertencias y errores. No fue ejecución Windows.

Las cuatro regresiones nuevas de apariencia se ejecutaron primero con una política deliberadamente incompleta y sin la validación del enum: **35/39**, con cuatro fallos de comportamiento. Cubren la matriz de prioridad tema/sistema/contraste, el mínimo reversible de Modo fácil, entradas inválidas y persistencia real en disco. La matriz contiene 24 combinaciones (3 × 2 × 2 × 2); las pruebas de escala cubren 100/125/150/200 %, límites, NaN e infinito. La prueba de disco conserva privacidad, proveedor, marcadores y sesión; carga archivos antiguos con Oscuro/Modo fácil desactivado y preserva el archivo corrupto con un enum desconocido. Después de la implementación: **39/39**.

Para la versión del empaquetador se cambió primero la expectativa de la prueba real Git/CLI de reproducibilidad: exigir `Optimus_Browser_Windows_0.3.3_alpha.zip`. Contra producción 0.3.2 falló una aserción porque no existía ese nombre de salida; tras cambiar producción pasó. La fixture conserva además una guía histórica 0.3.2: quitar la guía actual 0.3.3 sigue siendo rechazo aunque la histórica esté presente. No se ejecutan los PE sintéticos de estas pruebas.

## Validación final realizada

SDK oficial .NET **10.0.403**, SHA-512 verificado antes de extraer; host y runtimes NETCore/ASP.NET Core **10.0.14**. Cada suite se compiló primero mediante `dotnet build <proyecto> -c Release -m:1` y después se ejecutó con `dotnet run --project <proyecto> -c Release --no-build`.

Desde `products/browser/windows`, salvo el backend indicado:

| Proyecto o comando | Resultado final |
| --- | --- |
| `tests/Optimus.Core.Tests/Optimus.Core.Tests.csproj` | 39/39 PASS |
| `tests/Optimus.Search.Tests/Optimus.Search.Tests.csproj` | 50/50 PASS |
| `tests/Optimus.Privacy.Tests/Optimus.Privacy.Tests.csproj` | 24/24 PASS |
| `tests/Optimus.Search.Tests/Optimus.Search.Tests.csproj`, desde `products/browser/search` | 44/44 PASS |
| `python -m unittest discover -s tools/release -v` | 21/21 OK |
| `dotnet build src/Optimus.App/Optimus.App.csproj -c Release -m:1 -p:EnableWindowsTargeting=true` | Compilación correcta |
| `dotnet build scripts/WindowsSmoke/Optimus.Windows.Smoke.csproj -c Release -m:1 -p:EnableWindowsTargeting=true` | Compilación correcta |

Total: **157 comprobaciones C# y 21 pruebas Python correctas**. Las seis compilaciones finalizaron con **0 advertencias y 0 errores**. Los once comandos finales devolvieron 0. Los comandos exactos, códigos, tiempos y logs se conservan localmente en `artifacts/033-release/results.json` y los `.log` del mismo directorio; el baseline permanece en `artifacts/033-baseline/`. Los logs RED de apariencia y de versión se conservan junto a los finales, sin sustituirlos por resultados verdes.

Se revisaron valores de paleta mediante cálculos sRGB: claro texto/página 15,45; secundario/panel 6,67; blanco/acento 6,65; cálido/página 6,48; oscuro texto/página 16,79; secundario/elevado 8,04; etiqueta/acento 11,35. Son comprobaciones de diseño de pares concretos, no certificación de todos los estados ni evidencia de representación nativa. La revisión de código corrigió el riesgo de que el texto explícito de filas de marcadores/privacidad ocultara el color de selección nativo; su ejecución sigue pendiente.

## Alcance de preparación e inventario

App, título, pie, estado inicial, helper, scripts y empaquetador declaran 0.3.3. La propuesta `ci/WindowsSmoke.workflow.yml` conserva su ubicación inactiva; solo cambió su argumento de versión del backend. No se ha registrado ni ejecutado un workflow Windows.

`SOURCE_MANIFEST_0_3_3.json` inventaría las fuentes seleccionadas de Windows y Search mediante longitud, SHA-256 e identificador Git de blob de los bytes actuales. Excluye su propio archivo; conserva los manifiestos anteriores y no los reinterpreta. Las fuentes nuevas deben estar seleccionadas por Git antes de empaquetar, porque el empaquetador usa `git ls-files --cached` y lee los bytes del árbol de trabajo. Un cambio posterior de esos bytes exige regenerar el inventario.

Esta preparación no publica ni empaqueta binarios reales 0.3.3. La etapa de entrega debe publicar los tres apphosts win-x64 autocontenidos desde el SHA público final, fijar el mismo SourceRevisionId, generar el catálogo con el CLI real y verificar estructura, avisos, fuentes, PE, CRC y cobertura SHA-256. Esas comprobaciones y sus hashes deben registrarse antes de atribuirlas a un ZIP. Los scripts PowerShell no se han ejecutado en esta preparación Linux.

## Aceptación pendiente

**UNRUN:** ejecución Windows de los apphosts publicados, Windows PowerShell 5.1, WPF/WebView2, consulta real de preferencias del sistema, temas en ventanas secundarias y menús abiertos, selección enfocada/no enfocada y alto contraste. También siguen pendientes teclado, retorno de foco, Narrador/NVDA, ancho 420 DIP, áreas de interacción de 44 DIP y zoom 200 %. Las tres observaciones de la [guía 0.3.3](GUIA_0_3_3.md) son tareas propuestas, no resultados de usuario.

Este entorno dispone de Linux; no hay endpoint Windows verificado en esta sesión. No se ha usado Wine, HTML ni una compilación como prueba de ejecución WPF. El router/almacenamiento no se presenta como ejecutor Windows. No se modifica el equipo personal.

**BLOCKED:** aceptación de búsqueda web general upstream. El índice de tres ayudas y Wikipedia explícita conservan sus límites. No se activan IA, voz, IoT, proveedores, pagos, cuentas ni infraestructura. El diagnóstico heredado sigue siendo preparación para Windows; sus resultados históricos no aceptan la interfaz nueva. La reversión usa la carpeta completa de la versión anterior, sin mezclar DLL ni migrar perfiles.
