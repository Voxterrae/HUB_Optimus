# Demo de interfaz de Optimus

Snapshot de la revisión MagicPath `466698922518265856`, componente `466697341487947776`, proyecto `466697303898607616`, exportado el 30 de octubre de 2026. [Vista interactiva existente](https://designs.magicpath.ai/v1/clear-creek-5865).

`components/OptimusTuInternetMSHumano.tsx` exporta `OptimusExperience` y `OptimusTuInternetMSHumano`; importa el CSS que se conserva a su lado. Ambos archivos son copias exactas de la revisión ya construida. El código consume React y los tipos TypeScript/DOM; no se han añadido dependencias a la raíz del repositorio.

Es un componente para integrar, **no una aplicación autónoma con toolchain y lockfile**. La publicación en Pages requiere una tarea posterior que cree un host React verificable, construya su salida estática y revise el resultado antes de copiarlo a `site/browser/`. El workflow Pages actual no compila este directorio.

## Interacciones que existen

- Inicio, Guardados, Guía y Ajustes; navegación inferior en móvil.
- Vista sencilla, texto grande, alto contraste, reducir movimiento y tema claro.
- Resultados fijos de ejemplo, añadir/quitar enlaces y validación básica de URL.
- Guía local con respuestas preparadas; no hay asistente remoto conectado.
- Aspecto privado rotulado como demostración; no activa incógnito ni protección real.

Los cambios y los guardados duran hasta recargar. No hay traducciones, voz, reconocimiento, biometría ni control IoT implementados. Esas capacidades siguen como propuestas en #2017.

## Assets

La revisión exportada conserva URLs normalizadas de MagicPath para sus dos iconos. `assets/` incluye las copias originales y procedencia para permitir su futura integración local sin depender de ese alojamiento. No se ha cambiado la resolución de assets en este snapshot ni se ha declarado que funcione sin conexión.

La compilación remota y las comprobaciones de interfaz previas no equivalen a una certificación WCAG ni a una prueba de navegación nativa. Los límites y la validación de esta importación están en [../VALIDATION.md](../VALIDATION.md).
