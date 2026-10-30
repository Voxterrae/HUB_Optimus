# Optimus - piloto web accesible

Compañero web de navegación con seis idiomas, búsqueda explícita en Wikipedia, enlaces guardados opcionalmente en el dispositivo y controles de voz local según compatibilidad. No sustituye al navegador nativo Windows ni controla dispositivos IoT.

No requiere dependencias de ejecución, herramientas de compilación, cuenta de producto, backend ni claves. La vista de aceptación puede estar protegida por el alojamiento privado; esa protección no forma parte del registro de usuarios de la aplicación.

## Uso y verificación

Servir `dist/` mediante un servidor HTTP estático. No abrir `index.html` como `file://`, porque los módulos necesitan el origen HTTP. En el entorno administrado se usa exclusivamente `sites-preview start <checkout>` para la inspección.

```sh
node --test tests/*.test.mjs
node --check dist/app.mjs
node --check dist/core.mjs
node --check dist/i18n.mjs
node --check dist/voice.mjs
```

La aplicación usa solo archivos locales del directorio `dist/`. No registra service worker ni garantiza uso sin conexión. Los enlaces externos abren otra pestaña; la privacidad y las protecciones del navegador anfitrión siguen siendo responsabilidad de ese navegador.

## Datos y voz

- Wikipedia recibe la consulta y datos habituales de una conexión solo al enviar una búsqueda. No se consulta mientras se escribe.
- Consultas, resultados, audio y transcripciones no se guardan por la aplicación.
- Preferencias y enlaces se persisten solo tras elegir recordarlos en este dispositivo. El almacenamiento denegado o corrupto utiliza estado de sesión y muestra aviso.
- La lectura solo elige voces que el navegador declara locales. El dictado exige reconocimiento local y un paquete disponible; no instala modelos ni usa una alternativa remota.
- La ausencia de voces o de reconocimiento local no impide buscar y usar la aplicación por teclado.

Las traducciones se han redactado para el piloto; la revisión con hablantes nativos y las pruebas con personas siguen siendo necesarias antes de declarar aceptación de accesibilidad.

## Fuentes y alcance

Diseño basado en la identidad de Optimus y HUB_Optimus, con copias exactas de sus dos marcas SVG. La fuente nativa 0.2 y la demo React original se conservan en la propuesta de importación #2018 de Voxterrae/HUB_Optimus. Este host estático es un incremento independiente.

El plan y la especificación viven en `docs/superpowers/`. La validación de entrega está en `docs/VALIDATION.md`; los límites operativos en `docs/TECHNICAL_OPERATIONS.md`.

## Despliegue

- **Vista privada:** alojamiento Sites para aceptación del piloto, sin cambiar el asistente existente.
- **GitHub Pages:** copiar exactamente `dist/` a `site/browser/` en la propuesta correspondiente. Su publicación requiere la revisión y fusión protegida del repositorio; este proyecto no modifica workflows ni fusiona por sí mismo.
- **Azure Static Web Apps:** publicar el mismo directorio. `ops/azure/azuredeploy.json` prepara exclusivamente un recurso Free. No se ha ejecutado, no activa cuenta ni integra repositorio/credenciales automáticamente. Ver `ops/azure/README.md` antes de cualquier operación.

No se activan pagos, suscripciones, Microsoft for Startups, Store, Azure Speech, identidades, secretos, dispositivos ni sesiones nativas en esta entrega.
