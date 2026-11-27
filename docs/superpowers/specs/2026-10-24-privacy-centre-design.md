# Centro de privacidad de HUB Optimus

## Decisión y alcance

La primera entrega implementa el centro nativo propuesto en la [incidencia
1984](https://github.com/Voxterrae/HUB_Optimus/issues/1984). El usuario aceptó
este diseño en la conversación del 24 de octubre de 2026. Esta referencia
registra el alcance funcional aceptado; no sustituye las autorizaciones
protegidas de GitHub ni autoriza publicación, contratación o cambios de
gobernanza.

El centro describe el almacenamiento y los controles existentes del sitio
público y Operator. No recibe solicitudes, ejecuta eliminaciones remotas ni
introduce seguimiento. La identidad jurídica del responsable, su canal privado,
el inventario de proveedores y los criterios de conservación requieren
verificación antes de presentar el aviso como definitivo.

## Alternativas

Se elige la primera entrega nativa recomendada: no necesita cuotas ni un nuevo
servicio remoto. Añadir ahora un gestor de consentimiento como Klaro incorpora
una dependencia sin servicios opcionales confirmados que gestionar. Borlabs
solo es compatible con WordPress y corresponde, en su caso, a otro alcance.

## Comportamiento

- Ruta `/privacy/`, con español, inglés y alemán y enlaces desde ambos pies.
- Estado de borrador visible mientras falte la verificación de publicación.
- Información sobre finalidades, datos locales, proveedores, transferencias,
  conservación, derechos y revisión humana. Cada dato desconocido se declara
  pendiente; no se inventan responsables, plazos, proveedores o contactos.
- Inventario de preferencias de idioma, borrador guardado, candidatos de
  aprendizaje y caché estática. Enlaces a los controles existentes de Operator;
  esta página no borra almacenes ni modifica decisiones de consentimiento.
- Diferenciar borrar datos de este dispositivo, copias exportadas, registros
  del alojamiento y solicitudes al responsable.
- No formulario ficticio ni enlace de correo hasta verificar un canal válido.
- Idioma por parámetro válido o idioma del navegador; cambiarlo no modifica
  el almacenamiento de Operator. Texto de respaldo legible sin JavaScript.
- Recursos locales únicamente; ninguna analítica, telemetría, cookie nueva,
  llamada a un modelo ni dependencia de terceros.

## Preparación para gobernanza de IA

La ampliación solicitada se documenta por fases en
`docs/privacy/ai_governance_readiness.md`. Se reutilizarán los inventarios y
contratos existentes para capacidades, datos, procedencia y revisión humana.
No se implementan ahora registros de conversaciones, clasificación jurídica
automática, backend de incidentes, autonomía, nuevas llamadas a proveedores ni
un cuadro de mando. Cada función posterior necesita una incidencia y alcance
propios. Los avisos deben corresponder a una capacidad realmente activa.

## Límites y aceptación

La configuración de borrador impide presentar un responsable/contacto
incompletos como verificados. Los valores se insertan como texto. Solo un
correo simple validado y marcado como verificado puede generar un enlace de
contacto; nunca se aceptan cabeceras de correo o esquemas arbitrarios.

Se comprobarán la evaluación de los campos pendientes, idioma y respaldo,
renderizado, enlaces, ausencia de tráfico opcional y preservación del
almacenamiento con datos sintéticos. Se ejecutarán las pruebas existentes
afectadas. La PR seguirá siendo borrador hasta resolver las condiciones de
publicación y el proceso protegido del repositorio.
