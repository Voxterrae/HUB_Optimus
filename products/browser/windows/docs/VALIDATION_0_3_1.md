# Validación del diseño nativo Windows 0.3.1

Fecha: 30 de octubre de 2026, Europe/Madrid. Incremento sobre la PR #2022, base pública `36ddae644e345c2cb88ed88d521b95ebbebb6260`; coordinación #2021. El SHA público final y la decisión humana se registran externamente en la nueva PR y el comentario de entrega. No se intenta incluir el SHA del propio documento.

## Cambio comprobable

El ejecutable WPF carga Assets/OptimusTheme.xaml desde App.xaml. MainWindow usa navegación compacta, pestañas en una fila desplazable, lateral adaptable y paneles de ayuda/ajustes cerrados al inicio. NativeHomeView incorpora buscador y acciones reales; OptimusSearchView usa tarjetas nativas. No se sustituye el navegador por una maqueta ni se modifica Core/backend/transporte de búsqueda.

El título del ejecutable y los metadatos de empaquetado son 0.3.1. La guía vigente es GUIA_0_3_1.md; las guías y manifiestos 0.2/0.3 se conservan como evidencia histórica, sin reescribir sus hashes.

## Evidencia de código y compilación

- SDK oficial .NET10.0.403, runtimes10.0.14; archivo SDK verificado con SHA-512 contra los metadatos oficiales. Proxy/CA/TLS conservados.
- Base fresca: Core35 + Search Windows47 + Privacy24 + backend39 =145 comprobaciones C#, 18 Python correctas.
- Tras integrar inicio, recursos y shell: compilación WPF Release con cero advertencias/errores. La revisión de código encontró cuatro problemas de interacción y uno menor de foco; una tanda corrigió todos y la re-revisión no encontró problemas nuevos.
- Regresiones corregidas: Escape solo restaura foco al cerrar un panel; los destinos se muestran al navegar/abrir pestaña; Ajustes conserva avisos privados pendientes; los cambios de apariencia actualizan ventanas nativas abiertas; el menú es un destino persistente de retorno de foco.
- Empaquetado0.3.1: las pruebas existentes se ejecutaron primero con el nuevo nombre/guía y fallaron contra el empaquetador anterior; después de actualizar versión/guía, 18 correctas. Usan PE sintéticos, nunca ejecutados. La entrega usa publicaciones win-x64 reales, verificadas por separado.
- Un primer run del trabajador Search dio46/47 por timeout en cancelación TLS mientras se ejecutaba la base en paralelo. Se conserva como fallo observado; el run serial posterior dio47/47. No se atribuye una causa demostrada ni se cambió transporte para ocultarlo.

Comandos: `dotnet build <proyecto> -c Release -m:1` y `dotnet run --project <proyecto> -c Release --no-build` para las tres suites Windows y la del backend; `python -m unittest discover -s products/browser/windows/tools/release -v`; `dotnet build products/browser/windows/src/Optimus.App/Optimus.App.csproj -c Release -p:EnableWindowsTargeting=true -m:1`. El registro externo posterior vincula resultados finales al SHA distribuido.

## Referencia visual

MagicPath: componente467018221908791296, revisión467019243628662784, build completado. El render se inspeccionó como referencia del shell/inicio implementado. El HTML autocontenido refleja esa referencia y etiqueta expresamente que no es una captura del ejecutable. Conserva el logo original y no carga assets externos. No se afirma paridad de píxeles con WPF.

El navegador de QA local no estaba instalado. Su descarga oficial devolvió una página Site Unavailable; no se eludió la restricción. Por ello no se ejecutaron comprobaciones visuales multivista locales ni se atribuyen capturas de móvil/200% inexistentes. La adaptación a420DIP/200% se revisó como código y debe aceptarse en Windows con la lista de GUIA_0_3_1.md.

## Límites y aceptación pendiente

Windows físico, motor WebView2, geometría y recorte reales, teclado desde el HWND, foco/popup nativos, Narrador/NVDA, contraste alto/paleta del sistema y ventanas secundarias siguen pendientes de aceptación. Una compilación WPF en Linux y tests del núcleo no prueban esos resultados. Los pasos concretos de regresión están en la guía.

La alpha Windows carece de firma. La búsqueda web general sigue bloqueada por disponibilidad/relevancia upstream; este diseño no la resuelve ni activa voz, IA generativa o IoT. No cambia permisos, cuentas, infraestructura, CI, gobernanza, autoría Linux o el piloto web. Revisión humana y controles del repositorio siguen separados de esta validación técnica.

Reversión: usar la alpha anterior y retirar esta propuesta/ZIP; los perfiles siguen fuera de la carpeta de entrega. No hay migración destructiva. No actualizar la carpeta antigua parcialmente: extraer todo el ZIP nuevo, manteniendo Search/ junto a Optimus.exe.
