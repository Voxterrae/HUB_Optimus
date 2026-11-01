# Optimus Windows 0.3.2 alpha — arranque y diagnóstico

Extrae el ZIP completo en una carpeta nueva y abre `Optimus.exe`; conserva `Search/` y `Diagnostics/` junto a él. El título debe mostrar 0.3.2. El diseño nativo de 0.3.1 se conserva: inicio con buscador grande, tarjetas, menú y ajustes de tamaño/contraste. [Guía de interacción](GUIA_0_3_1.md).

Esta versión corrige un arranque en frío que podía detener el servicio de búsqueda hacia los dos segundos aunque disponía de cuatro. Ahora espera dentro del plazo completo y conserva la cancelación y el cierre de su propio proceso. También corrige una carrera de creación simultánea de la clave del servicio reproducida en Linux; conserva un archivo de bloqueo vacío junto al token y falla si no puede asegurar exclusión. Las regresiones se verifican con pruebas controladas; la ejecución del ejecutable en Windows sigue pendiente de evidencia real.

## Prueba cotidiana

1. En Inicio, pulsa **Tu índice**.
2. Busca **servicio local**. El catálogo incluido contiene tres ayudas públicas; debe aparecer «Ayuda Optimus: servicio local y privacidad».
3. Abre una dirección conocida desde la barra para probar la navegación WebView2. Este motor necesita WebView2 Evergreen instalado en Windows.

**Web** necesita un proveedor SearXNG del operador y aún no tiene aceptación de resultados generales. El catálogo de ayuda y Wikipedia no sustituyen un buscador mundial. Voz, IA generativa e IoT no están conectados. El modo privado limita persistencia local; no ofrece anonimato.

## Diagnóstico del servicio en Windows

El ZIP incluye el diagnóstico autocontenido; no necesitas SDK .NET ni PowerShell 7. Cierra Optimus y abre Windows PowerShell en la carpeta que contiene `Optimus.exe`. Ejecuta:

```powershell
powershell.exe -NoProfile -File .\Test-OptimusWindows.ps1 -Publication $PWD.Path
```

Comprueba el host realmente publicado: arranque, identidad TLS, rechazo de credenciales incorrectas, autorización y resultado del catálogo. Usa un puerto y una carpeta temporal propios; no lee perfiles ni el token habitual. Al terminar indica la ubicación de `result.json` y `metadata.json`. Código 0 significa que las comprobaciones solicitadas pasaron; 1 indica fallo y 3, un requisito de interfaz no disponible. Una prueba del servicio no acepta la ventana ni toda la seguridad del navegador.

Para vincular la ejecución al código distribuido, añade `-SourceCommit` con el SHA completo de la PR de entrega. Antes de ejecutar, comprobará ese SHA en ProductVersion de los tres ejecutables, sus DLL de entrada y las dos copias de Optimus.Core.dll. Sin ese argumento registra `not-requested`; no acredita la procedencia del código. Los hashes no equivalen a firma digital.

Si la política de scripts o SmartScreen bloquea la alpha, conserva las protecciones y aplica la política de tu equipo. El diagnóstico no modifica esas políticas ni instala software.

## Prueba de interfaz aislada

El parámetro `-Gui` es exclusivamente para una VM o usuario Windows desechable, con escritorio interactivo, WebView2 instalado y sin carpeta `%LOCALAPPDATA%\Optimus`. Se bloquea si encuentra un perfil existente o el puerto habitual ocupado. No ejecutarlo en tu usuario diario.

En ese entorno, el mismo comando con `-Gui` prueba inicio nativo, índice, guía local, una página loopback, pestaña privada, ajustes, cierre y captura de la ventana propia. Conserva el perfil recién creado para diagnóstico; descarta después la VM o el usuario. La ausencia de escritorio, WebView2, UIAutomation o captura utilizable produce bloqueo, nunca aceptación.

Este recorrido no sustituye teclado real, Narrador/NVDA, zoom 200%, geometría, navegación pública o pruebas de privacidad completas. Sus evidencias Windows aún no se han producido en el entorno Linux de preparación. La propuesta CI incluida bajo `Source/Windows/ci/` está inactiva y requiere el proceso protegido del repositorio.

## Procedencia y reversión

Alpha privada sin firma. `SHA256SUMS.txt` cubre el contenido y el `.sha256` externo cubre el ZIP. [Validación](VALIDATION_0_3_2.md) distingue pruebas realizadas y pendientes. No copies perfiles, tokens ni informes con datos personales a la carpeta de entrega. Para volver atrás, abre la carpeta completa de la alpha anterior; no mezcles sus DLL con esta versión.
