# Conoce HUB_Optimus

**Propuesta de explicación pública para revisión editorial.** Related to #2187.
Fuentes inspeccionadas el 14 de noviembre de 2026. Esta guía explica el proyecto;
los documentos originales mantienen su autoridad y su estado.

## Una idea sencilla

HUB_Optimus es la plataforma matriz creada y dirigida por **Benjamin Gerrit Hoff**
para desarrollar herramientas que ayuden a trabajar con información y tomar
decisiones con evidencia y responsabilidad humana.

El trabajo se organiza alrededor de una pregunta práctica: **¿qué sabemos, en
qué nos apoyamos, qué falta comprobar y quién decide el siguiente paso?**
Sus herramientas permiten preparar y revisar partes de ese trabajo. Algunas
ya tienen prototipos utilizables; otras necesitan integración, pruebas con
personas o una decisión de lanzamiento. El catálogo muestra esa diferencia.

## Un ejemplo cotidiano

Imagina que recibes un texto y necesitas explicarlo a un colaborador. Con el
Operator público puedes pegarlo y preparar un borrador estructurado. Después
revisas las afirmaciones y las referencias, señalas las dudas y conservas el
resultado para que una persona decida cómo continuar.

La versión pública trabaja con texto pegado. Introducir una URL como referencia
no significa que el sistema descargue, compruebe o certifique su contenido.
Otros componentes, como Search, un navegador o un conector administrativo,
tienen funciones y condiciones propias. El recorrido completo entre todas las
piezas todavía requiere sus pruebas y aceptación.

## Cómo ha evolucionado

El historial público empieza el **12 de diciembre de 2025**, con documentos
exploratorios sobre paz, diplomacia y estabilidad. Esa preocupación por los
incentivos, la comprobación y la responsabilidad sigue presente. El proyecto
ha ampliado su alcance hacia herramientas para organizar fuentes, preparar
expedientes, buscar documentación y revisar trabajo técnico.

| Hito de fuente | Qué representa | Evidencia |
| --- | --- | --- |
| Diciembre de 2025 | Primer registro y archivo de la exploración inicial | [Primer commit](https://github.com/Voxterrae/HUB_Optimus/commit/c7dd0f6da3a97fe52ad2ce025f87842d4ca6e9ac), [archivo](../../legacy/v0_exploratory/) |
| Junio de 2026 | Incorporación del sitio estático y del Operator | [Sitio](https://github.com/Voxterrae/HUB_Optimus/commit/70bc1f61d0316608133b6db6ec235fd1d1b5312c), [Operator](https://github.com/Voxterrae/HUB_Optimus/commit/b19a316cbd4603541bbd4829446987e08a9ce2ba) |
| Septiembre de 2026 | Exploración visual de la arquitectura y el conocimiento derivado | [Project Intelligence](https://github.com/Voxterrae/HUB_Optimus/commit/c7d08b78d38148ffc6f84b9f2dd8541149d224ff) |
| Octubre de 2026 | Fuentes del navegador Windows y del piloto Web | [Windows](https://github.com/Voxterrae/HUB_Optimus/commit/4002b849d0c2614627fc876b89bce8e21556d3a9), [Web](../../products/browser/web/README.md) |
| Noviembre de 2026 | Catálogo, búsqueda y registro público de creaciones y aportaciones | [Catálogo](../../products/README.md), [registro](CONTRIBUTIONS_REGISTER.md) |

Son hitos de documentación o código. Sus fechas no certifican cuándo una
persona pudo utilizar un servicio publicado ni que cada componente esté listo
para producción. El archivo histórico conserva su condición no canónica.

## Qué puedes hacer según tu interés

- **Conocerlo:** sigue esta guía, el [catálogo](../../products/README.md) y los
  [aportes al ecosistema](ECOSYSTEM_CONTRIBUTIONS.md).
- **Probar una utilidad:** empieza por un caso público o sintético con
  [Operator](https://huboptimus.dev/operator/). La
  [lista de pilotos](CAPABILITIES_AND_PILOTS.md) explica qué resultado observar
  y qué falta aceptar antes del uso habitual.
- **Colaborar:** consulta el [proceso de contribución](../../CONTRIBUTING.md),
  prepara una aportación acotada y enlaza sus fuentes. El registro conserva
  crédito, estado y asistencia de IA; una propuesta y una integración son pasos
  distintos.

## Las reglas, explicadas

El proyecto conserva varios documentos porque responden a preguntas diferentes.
En esta guía encontrarás una explicación breve y el enlace al texto original.

| Pregunta | Explicación | Texto original |
| --- | --- | --- |
| ¿Quién responde por el proyecto? | Benjamin Gerrit Hoff es fundador, creador, propietario y autoridad humana final. Participar o aportar código no transfiere el control. Se preservan los derechos y el crédito de terceros. | [Carta de propiedad y autoridad](../governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md), [manifiesto de identidad](../../config/governance/owner_identity.v1.json) |
| ¿Qué principios orientan el trabajo? | Las cartas y el Kernel establecen principios y límites de evaluación y revisión. Su preámbulo forma parte del contexto y debe leerse con el texto completo. | [Charter](../governance/CHARTER.md), [Kernel](../governance/KERNEL.md) |
| ¿Qué significa la carta del núcleo de simulación? | Expresa principios y restricciones para ese núcleo. Su lectura no demuestra que el prototipo implemente automáticamente todos los mecanismos que describe. | [Carta del núcleo](../../KERNEL_CHARTER.md), [versión inglesa](../../KERNEL_CHARTER_EN.md), [contrato ejecutable](../architecture/runtime_contract.md) |
| ¿Qué fuente manda cuando dos páginas discrepan? | La fuente depende de la pregunta: autoridad, estado GitHub, comportamiento ejecutable o idioma. Las explicaciones y los resúmenes son vistas derivadas. | [Jerarquía de fuentes](../context/SOURCE_OF_TRUTH.md) |

El manifiesto conserva `RATIFICATION_PROPOSED` y la inscripción de una clave
física sigue pendiente. Una página legible, una cuenta o un commit verificado
por GitHub no cambian ese estado ni equivalen a una firma física independiente.

## Idiomas y acceso

La metodología v1 tiene fuente canónica española; las demás superficies
conservan la política de su dominio. Hay interfaces y documentos en varios
idiomas con grados distintos de cobertura. El selector de una interfaz no
significa que toda la documentación esté traducida.

La presentación propuesta mostrará el idioma real, la revisión pendiente y una
fuente alternativa cuando falte traducción. Los documentos privados y los datos
de clientes no se incorporan a la lectura pública. Consulta la
[política de idiomas](../context/STATUS.md) y el
[registro de madurez](../i18n/maturity.v1.json).

## El siguiente paso propuesto

Demostrar una utilidad completa con una persona y un caso acotado. Registrar
qué funcionó, qué tuvo que corregirse y qué condiciones faltan para usarlo de
forma habitual. Esa evidencia permitirá ampliar el sistema con un propósito
concreto, manteniendo la decisión y la responsabilidad humanas.
