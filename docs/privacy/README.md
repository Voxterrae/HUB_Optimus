# Centro de privacidad

## Estado de la entrega

La incidencia [1984](https://github.com/Voxterrae/HUB_Optimus/issues/1984)
define un centro informativo nativo en `site/privacy/`. El diseño se aceptó en
conversación el 24 de octubre de 2026; esta nota no constituye aprobación de
merge o despliegue. El aviso permanece en preparación y no es una declaración
definitiva ni una certificación de cumplimiento.

El centro se limita al sitio público y sus controles locales. No contiene
backend, formulario, telemetría, borrado de datos, nueva cookie ni integración
con un proveedor de IA. El idioma se cambia en memoria; no se lee ni modifica
la preferencia persistente de Operator.

## Inventario técnico observado

Fuente: `main@fe789f78baddb3723547741211dd8f34b86fe292`, inspeccionada el
24 de octubre de 2026. La tabla describe código, no certifica un alojamiento
externo ni su configuración actual.

| Almacén | Dato y finalidad | Conservación y control existente |
| --- | --- | --- |
| localStorage `hub_optimus_language` | Idioma elegido en el sitio o Operator | Hasta eliminación mediante ajustes del navegador o sustitución por otra elección. |
| localStorage `hub_optimus_operator_case_v1` | Caso completo guardado expresamente | Hasta sustituirlo o usar `delete_saved_draft`. Limpiar campos no elimina esta copia. Abrir `advanced_operator_console`. |
| IndexedDB `hub_optimus_operator_learning_v1`, almacén `learning_store` | Candidatos de revisión creados o importados | Hasta su eliminación mediante los controles existentes de registro/caso. Abrir `learning_workspace`; no equivale a publicación del proyecto. |
| CacheStorage `hub-optimus-operator-*` y service worker | Recursos estáticos del Operator público | Reemplazo de versión o eliminación de datos del sitio. No debe confundirse con un almacén de casos. La superficie privada tiene exclusiones propias. |
| Exportaciones, portapapeles y compartición explícita | Copias creadas por el usuario fuera del almacén local | Una eliminación local no elimina esas copias. El centro no las enumera ni modifica. |
| Alojamiento y posibles registros | Puede incluir datos técnicos de visitantes | Proveedores, transferencias, finalidades y plazos efectivos pendientes de verificación. |

## Condiciones para completar el aviso

Editar `site/privacy/privacy-config.v1.js` únicamente con información
verificada y revisada:

1. Identidad adecuada del responsable y su condición en cada tratamiento.
2. Un canal privado válido y verificado para privacidad.
3. Descripción ES/EN/DE de alojamiento, proveedores, registros y transferencias.
4. Descripción ES/EN/DE de conservación y supresión, incluidos registros
   remotos, obligaciones aplicables y límites de las copias.
5. Revisión del aviso, finalidad, bases aplicables, información de derechos y
   recursos ante la autoridad competente que correspondan al despliegue.

`assessPublication` comprueba únicamente campos y marcadores de revisión.
Los marcadores son afirmaciones del operador: no prueban identidad, revisión
jurídica, recepción de correo, cumplimiento ni cambios en servicios externos.
Un nombre vacío, correo inseguro, descripción traducida incompleta o revisión
ausente mantiene el estado de borrador. La identidad no se deduce de la
titularidad del proyecto ni el contacto de un perfil de GitHub.

La configuración inicial conserva todos los marcadores sin verificar y no
incluye un contacto ficticio. La página indica su estado y lleva `noindex`.
Antes de publicar un aviso final deben completarse las verificaciones y el
proceso protegido del proyecto. Un aviso final también requiere una revisión
de contenido; el comprobador de campos no la sustituye.

## Validación y límites

- Pruebas de la evaluación de publicación, correo seguro e idioma.
- Validador existente de rutas, referencias y fragmentos, ampliado con `/privacy/`.
- Pruebas existentes del catálogo de Operator; los catálogos y sus versiones
  permanecen intactos porque los enlaces reutilizan textos ya traducidos.
- QA de navegador prevista con datos sintéticos, solicitudes de recursos solo
  locales, idiomas, móvil y respaldo sin JavaScript. No se usa una sesión real
  del usuario. La revisión visual sigue pendiente: el entorno no dispone de
  Chromium y su descarga no produjo un archivo válido. No se declara superada.

La revisión independiente detectó y corrigió enlaces relativos que habrían
fallado en la superficie privada: ambos pies apuntan explícitamente al centro
público. La prueba de resolución contempla los orígenes público y privado.
También se endureció la sintaxis del correo para evitar contactos malformados.
Las regresiones se observaron fallar antes de corregirlas.

Validación local del 24 de octubre de 2026: **57 pruebas focalizadas superadas**
(`test_privacy_centre`, enlaces públicos, i18n de Operator e interacción estática).
También pasan la comprobación de sintaxis de JavaScript, codificación y
`git diff --check`.

La suite general no se declara verde en este entorno. La primera ejecución
registró un fallo por historial Git incompleto, resuelto al recuperar el
historial y repetir la prueba de adopción antigua, y tres fallos de
`test_unmodified_production_supervisor_crosses_real_uid_boundary` en
`tests/test_ec2_validation_boundary.py` (`passes`, `fails`, `delayed-descendant`).
Los tres se reprodujeron también sobre una copia íntegra del commit base sin
este cambio. No se modifican controles EC2 ni se omiten esas pruebas para hacer
pasar esta entrega. La revisión y el CI del repositorio conservan sus gates.

Pendiente menor de la revisión: la metadescripción inicial permanece en español
al cambiar de idioma; el título y el contenido sí cambian. El aviso provisional
lleva `noindex`, y este detalle debe revisarse antes de un aviso final indexable.

La ruta queda fuera del ámbito del service worker de Operator y no se añade a
su precaché. La página pública de Operator ya obtiene su HTML de la red antes
de usar respaldo, pero las instalaciones sin conexión pueden conservar un pie
anterior. No se afirma que una PWA sin conexión haya recibido la actualización.

La preparación futura de IA se documenta en
[el plan de preparación](ai_governance_readiness.md). Sus recomendaciones no
activan controles, no clasifican jurídicamente los sistemas y no amplían su
autoridad. Cualquier CMP, canal automatizado, seguimiento o cambio de proveedor
requiere un alcance posterior.

## Reversión

Revertir esta única PR retira el centro y sus dos enlaces. No hay migración de
datos, cambio de consentimiento, limpieza de almacenamiento ni servicio remoto
que deshacer.
