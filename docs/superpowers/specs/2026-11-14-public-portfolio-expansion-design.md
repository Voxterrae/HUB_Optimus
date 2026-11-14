# Relato, catálogo y lectura pública de HUB_Optimus

Related to #2187. Refs #2185 y #1936; las tres incidencias permanecen abiertas.

**Estado: propuesta editorial preparada para aprobación humana.** No autoriza
modificar textos normativos, implementar el generador o publicar una superficie.
Base inspeccionada: `53b7a841e028592ca81fb43d04d15a2b017bbd78`, 14-11-2026.

## Intención y público

Una persona nueva debe entender qué es HUB_Optimus, quién responde por él, una
utilidad que puede probar y los límites de ese resultado. Una persona que quiera
colaborar debe encontrar cómo aportar y cómo se conserva su crédito. Un lector
técnico debe poder pasar de cada explicación a su fuente exacta.

El origen diplomático se presenta como parte de la historia. La definición
actual como plataforma matriz procede de los documentos de autoridad vigentes;
no se redacta una nueva constitución ni se inventa una biografía personal.

## Enfoques considerados

| Enfoque | Ventaja | Coste y decisión propuesta |
| --- | --- | --- |
| Una base editorial en el repositorio, HTML estático derivado y espejo Sites | Conserva procedencia, versiones y contenido común; utiliza hosting y revisión existentes | Recomendado. Necesita un paso de generación acotado y comprobación de enlaces |
| Editar web y Sites por separado | Permite cambios visuales independientes | Duplica mantenimiento y dificulta saber qué texto está vigente; no se propone |
| Migrar a un portal/framework nuevo | Ofrece capacidades editoriales amplias | Añade dependencias y migración sin necesidad demostrada; no se propone |

La recomendación conserva la arquitectura pública actual y la preferencia del
propietario por reflejar la misma información en README, huboptimus.dev y Sites.
La elección final del alcance editorial sigue pendiente de revisión del texto.

## Recorrido de lectura propuesto

1. **Conoce HUB_Optimus:** definición breve, ejemplo cotidiano, persona
   responsable y origen. Borrador completo: [Conoce HUB_Optimus](../../project/HUB_OPTIMUS_EXPLAINED.md).
2. **Qué puedes probar:** catálogo con madurez, utilidad, coste incremental y
   siguiente aceptación. No sustituye el registry de capacidades.
3. **Cómo se ha desarrollado:** hitos con fecha y fuente, archivo histórico,
   creaciones y aportaciones con crédito real. Mantener el índice Git completo.
4. **Cómo se gobierna:** explicación breve no normativa, preámbulo y documento
   completo; fuente, ruta, idioma, fecha y SHA visibles.
5. **Cómo colaborar:** trabajo acotado, propuesta, pruebas, revisión humana y
   registro del estado; sin insinuar aceptación del proveedor por usar su API.

Los primeros pilotos se proponen en [el catálogo](../../project/CAPABILITIES_AND_PILOTS.md).
El inventario ampliado de [trabajo en el ecosistema](../../project/ECOSYSTEM_CONTRIBUTIONS.md)
distingue creación, integración, envío y aceptación. No hay un objetivo de
inflar el número de productos ni de atribuirse parches de otras personas.

## Contrato de lectura de Markdown

Usar una lista explícita de documentos públicos. El primer lote comprende la
guía explicativa, catálogo, registro de contribuciones, Founder Charter,
Charter, Kernel y las cartas ES/EN del núcleo de simulación.

- La explicación ocupa una capa identificada como no normativa. El documento
  original permanece íntegro, incluido el preámbulo; no se recortan reservas.
- Generar desde un commit fuente explícito, con ruta y SHA-256. Si fuente y
  derivado cambian juntos, separar el commit de fuente del commit de generación.
- Renderizar mediante una herramienta mantenida, evaluada y fijada como
  herramienta editorial. La dependencia exacta se propone después de aprobar
  este diseño; no se incorpora un parser propio ni un framework nuevo.
- Escapar código y sanear HTML/URLs. No admitir scripts, rutas arbitrarias,
  archivos privados o enlaces de acceso como entradas.
- Convertir enlaces relativos solo cuando su destino exista en el lote; en los
  demás casos, abrir la fuente exacta en GitHub con su idioma visible.
- HTML legible sin JavaScript, índice de títulos, tablas con lectura móvil,
  foco visible, teclado y `lang`/`dir`; aislar código y nombres técnicos en RTL.
- Añadir generación y comprobación de diferencias sin escritura. Extender de
  forma explícita el inventario de siete rutas HTML y sus pruebas de enlaces.
- Versionar los derivados dentro de `site/docs/`; conservar el workflow Pages
  existente que publica `site/`. No activar despliegues desde esta propuesta.

## Idiomas y cobertura

La primera meta es **navegación completa y honesta**, con variantes reales y
fallback explícito. Completar la traducción de todas las normas requiere lotes
posteriores y revisión lingüística. No tratar un stub como traducción terminada.

| Idioma | Onboarding actual, 3 documentos | Gobernanza actual, 18 documentos | Disposición propuesta |
| --- | --- | --- | --- |
| EN | 3 baseline parity | 18 canonical según manifiesto de docs | Fuente de docs por dominio; no confundir con paridad de todo v1 |
| ES | 3 review-needed | 10 review-needed, 8 stub | Primer relato explicativo; conservar fuente canónica española de metodología |
| DE | 3 review-needed | 13 review-needed, 5 stub | Resumen y navegación, revisión pendiente visible |
| CA, FR, RU | 3 stub por idioma | 5 review-needed, 13 stub por idioma | Explicaciones acotadas; usar fuente alternativa mientras falte documento |
| HE, RTL | 1 review-needed, 2 missing | 1 review-needed, 17 stub | No publicar missing como enlace traducido; validar RTL y contenido mixto |
| ZH-Hans | 1 stub, 2 missing | 1 review-needed, 17 stub | Simplificado; fuente alternativa y estado visible |

Fuente de esta tabla: `docs/i18n/maturity.v1.json` a la base indicada. La auditoría
estructural pasó sin errores ni avisos; no certifica revisión profesional.
La matriz core ES/EN conserva 51/51 disposiciones humanas `UNRESOLVED`.
La interfaz del portfolio admite EN/ES/DE/RU/HE/ZH-Hans; Browser Web emplea otro
conjunto que incluye CA/FR. Los selectores no se mezclan automáticamente.

No cambiar canonicalidad ni ratificación. El Founder Charter contiene sus
propios estatus de texto canónico y renderings; esa particularidad debe
conservarse al publicar, sin atribuirle el estatus genérico de otro documento.

## README y coherencia

Presentar primero una explicación de uso y enlaces por interés. Conservar el
bloque de fundador, derechos y autoridad. Enlazar el relato, catálogo y fuentes;
evitar que el lector tenga que abrir un JSON para comprender la historia.
La descripción de la portada debe aclarar que el Operator público trabaja con
texto pegado y que una URL por sí sola no supone recuperación ni verificación.

Corregir después, como cambio editorial acotado, el onboarding que llama a STATUS
autoridad general: la jerarquía aplicable es SOURCE_OF_TRUTH y STATUS gobierna
idiomas. No modificar Charter/Kernel para resolver una explicación simplificada.

## Publicación y Sites

Tras aprobación del relato y PR protegida, verificar el SHA, el artefacto y los
bytes servidos de Pages. Sincronizar después el **Site existente** desde ese
mismo árbol, conservando audiencia y registrando su versión y procedencia.
No crear otro Site ni convertir un acceso restringido en público.

El Site principal conserva versiones y redirecciones propias. Leer versión viva
y guardada antes de decidir qué sustituir; una versión numerada no demuestra
qué contenido está servido. Studio y los accesorios operativos se inventarían
por separado y no se transforman en espejos públicos del repositorio.

## Aceptación y orden

1. Aprobar el relato de la guía y el primer piloto con un resultado observable.
2. Implementar el lote de lectura Markdown y la navegación; validar procedencia,
   enlaces, texto íntegro, idiomas/fallback, teclado, móvil y RTL.
3. Integrar mediante los controles vigentes y obtener recibo de publicación
   Pages; sincronizar el espejo y comprobar su versión por separado.
4. Ampliar traducciones y pilotos con sus propias evidencias de aceptación.

El bloqueo actual es editorial/de aceptación, no la necesidad de otro proveedor.
No se han cambiado productos, contratos, dependencias, autoridad, permisos o
audiencias. El coste nuevo dominante es la revisión humana y mantenimiento;
no se justifica un servicio recurrente adicional para esta entrega.
