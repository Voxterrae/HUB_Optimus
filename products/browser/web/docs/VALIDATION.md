# Validación del piloto web accesible

Fecha de entrega: 2026-10-30. Esta evidencia corresponde al nuevo módulo estático; no acredita aceptación del navegador nativo Windows ni del asistente existente.

## Verificación automatizada

`node --test tests/*.test.mjs`: **53 pruebas, 53 correctas**, sin fallos, cancelaciones, omisiones ni tareas pendientes. Desglose:23 núcleo,5 idiomas,23 voz,2 de ayuda hablada en la aplicación. Se comprobaron también sintaxis de los cuatro módulos con `node --check` y `git diff --check`.

El P2 de ayuda hablada se reprodujo antes del arreglo: con interfaz inglesa y voz española se preparaba texto inglés, y con interfaz española y voz inglesa se preparaba texto español. Las dos pruebas de `tests/app.test.mjs` fallaron por esa diferencia de texto (RED) y pasaron después (GREEN). Importan `app.mjs` y ejecutan sus manejadores reales de selección y lectura, junto con las traducciones y `VoiceController` de producción. Verifican el texto completo, el locale de la petición y de la voz elegida, y que el idioma visible no cambie. El DOM mínimo y las APIs de síntesis son dobles de los límites del navegador; no son pruebas de audio físico, voces instaladas o navegador real. El espejo `site/browser/` conserva los mismos bytes que `dist/`.

La suite Node también se ejecuta desde `tests/test_browser_web_node_suite.py`, descubierto por el `python -m pytest -q` existente de CI. El adaptador exige Node, enumera los archivos `*.test.mjs` y propaga cualquier fallo; no omite la regresión si falta el runtime. Se verificó que este recorrido pytest falla con el comportamiento anterior y pasa con la corrección. Los controles remotos se comprueban por separado sobre el SHA final.

Las pruebas ejercitan funciones de producción: hosts/opciones de búsqueda, IDs y URLs válidos, consultas/resultados acotados, streams reales y límite1MiB, cancelación y plazo10s incluso ante transporte que ignora AbortSignal; persistencia opt-in, esquema, máximo50 enlaces, título120 y URL2048, errores y borrado de clave propia; rechazo HTTP/redirección/cuerpo ausente/tamaño anunciado con aborto y cancelación de recursos antes de resolver el error, exclusión de borradores sin terminar de la persistencia; seis diccionarios y parámetros; voz explícitamente local y ciclo de reconocimiento, permisos,30s, cancelación y reentrancia. No prueban un micrófono físico ni la disponibilidad de paquetes del sistema.

Regresiones corregidas con evidencia RED/GREEN: cinco casos de reemplazo reentrante de sesiones de voz; límite de títulos de respaldo al leer/escribir; diálogo de privacidad eliminado por un resultado pendiente; foco perdido tras guardar un resultado. Los dos últimos se reprodujeron y verificaron con el navegador real, no con un DOM simulado.

La revisión final añadió cuatro regresiones de limpieza de respuestas rechazadas con streams reales (RED/GREEN) y una comprobación de que los borradores no entran en la persistencia. El formulario conserva el borrador solo en memoria durante esta sesión; se borra al guardar correctamente. En navegador real, el cambio de idioma y la navegación conservan ambos campos; eliminar otro enlace conserva el borrador, guardar correctamente lo vacía y Borrar datos lo descarta explícitamente. La reproducción RED de idioma y su GREEN se confirmaron en la interfaz real. El recorrido a otra pestaña y vuelta conservó los datos, pero el navegador de pruebas no expuso una transición hidden verificable; esa aceptación específica queda pendiente en dispositivo.

JSON local: manifiesto web, configuración de cabeceras y plantilla ARM. La validación sintáctica no acredita compatibilidad del proveedor Azure.

## Navegador real

- Módulos, estilos y marcas cargaron en la vista administrada. Búsqueda explícita real de «navegador web» a Wikipedia en español: diez resultados y enlaces por pageid. No se utilizó una respuesta ficticia para esta comprobación de red.
- Modal con respuesta controlada retrasada4s: abierto antes de la respuesta, permanece abierto y conserva Close al finalizar. Cierre y Escape devuelven foco al botón actual. El fixture se retira del artefacto publicado.
- Guardar mediante Enter conserva foco en el estado guardado; Enter repetido no duplica el enlace; Tab continúa. Eliminar el último enlace coloca foco en Título del enlace.
- Seis idiomas en Inicio y Ajustes a320px (305px de contenido por la barra de desplazamiento): sin desbordamiento horizontal medido. Ajustes a26px, claro, contraste alto y movimiento reducido se mantuvieron legibles. Idioma de interfaz independiente del de voz.
- Al elegir recordar, preferencias y un enlace HTTPS de prueba reaparecieron tras recarga. El formulario rechazó javascript:. Borrar datos eliminó la persistencia y la siguiente recarga mostró los valores iniciales y recuerdo desactivado. Los datos de prueba se retiraron.
- Lectura sin voz local y dictado sin paquete instalado mostraron alternativas escritas; no se concedió micrófono ni se descargó un modelo.

## Límites de aceptación

Pendientes: móviles físicos, micrófono/paquete local real, lectores de pantalla, participantes mayores/con discapacidad, traducciones con hablantes nativos y zoom real del navegador al200%. Los atajos del navegador de pruebas no cambiaron su escala; no se presenta la prueba a320px como sustituto de esa aceptación. Tampoco se certifica conformidad completa de accesibilidad, protección universal ni idoneidad de cada contenido externo.

No hay service worker ni garantía sin conexión. Es una aplicación web compañera con búsqueda Wikipedia, no un motor que indexe toda la web. No cambia sesiones privadas, no califica webs por ética, no ejecuta acciones de IoT y no incorpora IA generativa o voz remota.

## Publicación y operación

La vista de aceptación privada se publica separadamente del repositorio principal. El SHA remoto y versión se registran en el resultado de despliegue, y la propuesta GitHub identifica su propio SHA exacto. La copia para Pages debe coincidir byte a byte con `dist/`, comprobado antes del envío. No se incluyen configuración privada del host, fixtures, claves ni documento de organización privado en la propuesta pública.

GitHub Pages requiere integración protegida y evidencia posterior del workflow. Azure Static Web Apps Free es un destino preparado: sin validación del proveedor, recursos, credenciales, suscripción o consumo activados. Revisiones técnicas no sustituyen la decisión humana ni las comprobaciones de GitHub.
