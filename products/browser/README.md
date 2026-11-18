# Optimus Browser

Related to #2021.

## Fuentes del módulo

| Componente | Qué contiene el repositorio | Guía o seguimiento |
|---|---|---|
| Windows | Aplicación WPF/WebView2. El proyecto declara `0.3.3-alpha`. La distribución firmada y la aceptación con tecnologías de apoyo requieren evidencia propia. | [Guía de Windows](windows/README.md) · [versión del proyecto](windows/src/Optimus.App/Optimus.App.csproj) |
| Search | Servicio local compartido con un catálogo finito. La búsqueda web requiere una instancia SearXNG configurada por el operador. | [Guía de Search](search/README.md) |
| Piloto web | Interfaz en seis idiomas con búsqueda explícita en Wikipedia. La voz local depende de las capacidades del navegador y del dispositivo. | [Guía del piloto web](web/README.md) |
| Linux | El seguimiento y las entregas propuestas se documentan en la incidencia de coordinación. | [Seguimiento de Windows y Linux](https://github.com/Voxterrae/HUB_Optimus/issues/2021) |

## Importación original del 30 de octubre de 2026

La propuesta de [#2017](https://github.com/Voxterrae/HUB_Optimus/issues/2017) preservó las fuentes de **Optimus para Windows 0.2 alpha** y la **demo adaptable de interfaz**. Las notas siguientes describen el alcance de esa importación.

| Componente | Estado verificable | Ubicación |
|---|---|---|
| Navegador Windows | WPF/WebView2, alpha sin firma; pruebas reales en Windows de esta versión pendientes | [windows/](windows/README.md) |
| Interfaz adaptable | Demo React en español: vista sencilla, texto grande, contraste, movimiento reducido, tema claro, guardados temporales y guía local | [demo/](demo/README.md) |
| Idiomas, voz e IoT | Requisitos propuestos en la issue; no implementados en esta importación | [#2017](https://github.com/Voxterrae/HUB_Optimus/issues/2017) |

La demo actual está disponible en [MagicPath](https://designs.magicpath.ai/v1/clear-creek-5865). La búsqueda muestra resultados fijos y el aspecto privado no cambia la privacidad del navegador anfitrión. La demo no sustituye al navegador nativo ni navega dentro de páginas de terceros.

### Objetivo inclusivo propuesto

Una misma herramienta para mayores, personas con necesidades de accesibilidad y usuarios avanzados. Personalización elegida por la persona: sin inferir edad, discapacidad, diagnóstico o habilidad. La siguiente especificación debe separar interfaz, contenido, voz y permisos; probar tareas reales con personas y conservar alternativas a la entrada por voz.

La issue propone tres niveles de densidad —sencillo, equilibrado y avanzado—, idiomas revisados, lectura en voz alta, reconocimiento mediante pulsar para hablar y conexión acotada con dispositivos. Estas capacidades no se presentan como disponibles por haberlas documentado.

### Despliegue y revisión de la importación

- Esta importación solo añade `products/browser/`. No cambia `site/`, CI, runtime principal, Kernel, reglas, permisos o el asistente privado.
- El workflow Pages actual publica `site/` directamente y no construye esta demo React. La publicación estática se plantea como incremento posterior con revisión propia.
- El navegador real se distribuye como aplicación nativa. Las integraciones que precisen ejecución o credenciales requieren un backend o puente privado; no se guardan secretos en Pages.
- No se añaden dependencias, servicios de pago, telemetría o integración de micrófono/dispositivos en esta importación.

### Procedencia y validación de la importación

Consultar [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) y [VALIDATION.md](VALIDATION.md). Se preservan los avisos de terceros; los informes privados de revisión y los ejecutables no forman parte de este módulo.

Las normas del repositorio y [IP_NOTICE.md](../../IP_NOTICE.md) siguen siendo aplicables. La importación no cambia las licencias ni las declaraciones de autoridad.
