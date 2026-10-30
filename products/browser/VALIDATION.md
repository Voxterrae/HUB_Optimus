# Validación de importación — 30 de octubre de 2026

## Nota histórica — incremento del 30 de octubre de 2026

Este registro y SOURCE_MANIFEST.json describen los bytes de la importación 0.2 en #2018. No certifican la identidad de los archivos modificados después para 0.3 en #2021. Consultar [la validación nueva](search/docs/VALIDATION.md); sus hashes finales se generan por separado después de integrar. Los hashes originales permanecen intactos.

## Alcance

Importación de fuentes existentes para revisión en #2017. No se han activado integraciones ni modificado el comportamiento del navegador, el sitio principal o el asistente privado.

## Evidencias de origen

- Se comprobó SHA256 del ZIP 0.2: `e4eccc2fc9a9d3ebdd37020bb6132ec865ddd997ffe7e6257d108fc783be2a9d`.
- Las entradas nativas elegidas coinciden byte por byte con el archivo de origen. Sus rutas y hashes están en `SOURCE_MANIFEST.json`.
- Los dos archivos de interfaz React/CSS coinciden con la revisión final de MagicPath `466698922518265856`; el servicio devolvió compilación `completed`. Esa compilación es evidencia anterior a la importación, no una compilación nueva de este repositorio.
- Las copias SVG originales de las dos marcas se conservan con procedencia. No se cambia la resolución de assets del componente exportado.

## Comprobaciones de esta importación

- Suite existente de empaquetado Python ejecutada desde `windows/`: seis pruebas correctas. Comprueba selección, reproducibilidad, hashes y rechazos de entradas peligrosas usando repositorios temporales y cabeceras PE sintéticas.
- Verificación de hashes de todas las fuentes importadas y revisión de que la propuesta solo añade rutas bajo `products/browser/`.
- Revisión de procedencia, dependencias locales y exclusión de ejecutables, SDK, perfiles, secretos e informes privados.

Estas comprobaciones no ejecutan el navegador. El SDK .NET y PowerShell no están disponibles en el entorno de importación: las tres suites C#, la compilación WPF y los scripts no se han vuelto a ejecutar aquí. Las 80 comprobaciones históricas del artefacto 0.2 no se presentan como un nuevo resultado de esta PR.

## Límites y aceptación pendiente

- Ejecución Windows, cookies privadas, solicitudes de red, limpieza de perfiles y comportamiento COM.
- Teclado, Narrador/NVDA, escalado de 200 %, alto contraste y pruebas con personas de distintas necesidades.
- La demo fue probada manualmente en Chrome y en una vista de 402 × 874; no certifica iOS/Safari ni conformidad WCAG.
- La demo no incluye un host autónomo/toolchain/lockfile. Pages no construye ni publica este directorio.
- Revisión humana, firmas y checks exigidos por el repositorio pendientes. Una PR borrador no constituye autorización o despliegue.

La siguiente entrega debe ser un incremento acotado y verificable de accesibilidad y host de demo; idiomas, voz e IoT tienen aceptación separada en la issue. No se añaden esas funciones por documentarlas.
