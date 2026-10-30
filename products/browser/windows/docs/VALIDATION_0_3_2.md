# Validación de arranque y diagnóstico 0.3.2

Fecha: 30/10/2026, Europe/Madrid. Base pública del diseño nativo: `533057274a735a9bd6514b143ce14214e7642dfc` (#2025), coordinación #2021. El SHA público final y el hash del ZIP se registran en la PR y el comentario de entrega después de publicar. No se incluyen aquí identificadores autorreferentes.

## Hallazgos y correcciones

El launcher tenía un límite de veinte sondeos de 100 ms dentro de un plazo declarado de cuatro segundos. Con perfil nuevo y token todavía ausente podía cerrar su propio host hacia los dos segundos. Dos regresiones nuevas fallaron contra el código anterior (48/50); la cancelación ya pasaba. El bucle ahora consume únicamente el plazo existente de cuatro segundos y conserva TLS, pruebas de identidad y propiedad/cierre de procesos. La suite Search Windows pasó después 50/50.

La validación integrada encontró además un fallo anterior del backend: 38/39, convergencia de creación simultánea del token. Un probe aislado de veinte rondas de ocho llamadas devolvió claves distintas en cuatro rondas. Se reprodujo en Linux/overlayfs/.NET10.0.14; no se afirma que se reprodujera en Windows. La ruta Unix de File.Move puede comprobar ausencia y después renombrar, dejando una carrera entre escritores. La corrección mantiene un guard lateral vacío y persistente, exclusión FileShare.None verificada con una segunda apertura, permisos privados en Unix y espera cancelable de hasta cinco segundos. Recomprueba el destino bajo el guard y no borra el sidecar. Si no puede demostrar exclusión, falla antes de publicar. Regresiones RED39/44; GREEN44/44 con veinte rondas de ocho llamadas, ocho procesos independientes, cancelación, contención acotada y rechazo de locking desactivado/guard expuesto. Windows ejecutará42 casos; dos son específicos de Unix y no se les atribuye aceptación Windows.

## Diagnóstico preparado

Test-OptimusWindows.ps1 y el helper autocontenido reutilizan LocalSearchTransport de producción. El modo servicio arranca el SearchHost publicado con token/carpeta/puerto propios, valida TLS y health nonce/HMAC, rechazo de token incorrecto y búsqueda sin autorización, y exige el resultado real de una ayuda pública. Solo limpia sus procesos y temporales. Es preparación para una prueba Windows, no una prueba Windows ya ejecutada.

Con -SourceCommit, antes de ejecutar se exige ese SHA en ProductVersion de ocho PE: tres apphosts, sus tres DLL de entrada y las dos copias de Core. La revisión detectó y corrigió la omisión inicial de DLL administradas. Sin ese argumento, la procedencia figura como not-requested. Esta comprobación impide mezclar accidentalmente versiones; no es firma digital ni defensa frente a alteración deliberada de binarios sin firma.

GUI es opcional y exclusiva de un usuario/VM desechable sin perfil Optimus previo, con puerto libre, WebView2 y escritorio interactivo. Usa UIAutomation y una página loopback; captura solo el HWND propio y rechaza imagen uniforme. Retiene el perfil nuevo; hay que descartar el entorno. Requisitos ausentes se registran como bloqueo no satisfactorio. No prueba teclado físico, Narrador/NVDA, navegación pública ni privacidad completa.

## Evidencia de preparación en Linux

- SDK .NET10.0.403 y runtimes10.0.14. Builds seriales Core, Search Windows, Privacy, backend, WPF y helper sin advertencias ni errores. Core35, Search Windows50 y Privacy24 correctas. Backend44/44 después de corregir la carrera: total153 comprobaciones C# correctas en Linux. La primera ejecución fallida permanece registrada. La compilación inicial de una prueba nueva detectó CA1416; se añadió el guard de plataforma dentro del lambda antes de obtener RED/GREEN.
- Empaquetador: tres pruebas nuevas fallaron contra la validación anterior; después, 21/21. Se exige Diagnostics autocontenido, wrapper y dependencias, arquitectura AMD64 y runtimeconfig WindowsDesktop; se rechaza ausencia, x86 y dependencia de runtime instalado. Son PE sintéticos no ejecutados; la publicación real se valida aparte.
- Fixtures portables: 21/21 en Linux normal, locale ASCII y configuración Git global con autocrlf/safecrlf. UTF-8/LF explícitos. Linux conserva archivos reales con nombres incompatibles con Windows; los controles léxicos/ZIP y una entrada de directorio duplicada inyectada verifican esos rechazos sin exigir que NTFS represente dichos estados. Symlink omite únicamente la subprueba sin soporte/privilegio, de forma visible. La simulación Windows en Linux no es ejecución Windows.
- Parser PowerShell7.4: 979 tokens, cero errores en el wrapper final; esto no acredita comportamiento de WindowsPowerShell5.1. Parser temporal separado del producto; no se añade su dependencia a la entrega.
- YAML: permisos contents:read, Windows2022, acciones fijadas a SHA40, tres publicaciones y dos invocaciones ligadas al mismo SHA. Ubicado fuera de .github/workflows; no se activó ni ejecutó. No se usa un resultado CI Ubuntu como aceptación WPF.

## Publicación e integridad

La entrega contiene apphosts win-x64 reales del navegador, host y diagnóstico, con runtimes autocontenidos y avisos oficiales. El catálogo se genera con el CLI real e incluye tres ayudas. SourceRevisionId se fija al SHA público en las tres publicaciones. Los recursos ProductVersion se inspeccionan desde Linux; la lectura mediante Windows VersionInfo queda pendiente hasta ejecutar el diagnóstico. El empaquetador comprueba estructura, runtimes, rutas, privacidad, CRC y cobertura SHA256 completa. SOURCE_MANIFEST_0_3_2.json inventaría los bytes finales; los manifiestos anteriores se conservan sin cambios.

## Aceptación pendiente

**UNRUN:** ejecución del host publicado y PowerShell5.1 en Windows; WPF/WebView2/UIAutomation/captura/cierre reales; teclado, foco, 420DIP, zoom200%, contraste del sistema y tecnologías de apoyo. Este entorno solo dispone de Linux y no de un endpoint Windows verificado. No se accede al PC personal ni se habilita una ruta alternativa para eludir controles.

**BLOCKED:** relevancia/disponibilidad de búsqueda web general upstream. Índice local y Wikipedia siguen siendo fuentes explícitas, no evidencia de un índice mundial. No se activan proveedor, IA, voz, IoT, pagos o infraestructura.

**CI inactiva:** la propuesta necesita el proceso protegido de autoría/firma/revisión del propietario. El commit del conector no está verificado; no se registró workflow ni se modificaron protecciones. Esto no es un rechazo automático de herramienta y tampoco una aceptación humana. Reversión: carpeta completa de la versión anterior, sin mezclar DLL ni migrar perfiles.
