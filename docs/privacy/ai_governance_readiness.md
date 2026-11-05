# Preparación para la gobernanza de IA

**Estado:** recomendaciones prospectivas para revisión, vinculadas a la
[issue #1984](https://github.com/Voxterrae/HUB_Optimus/issues/1984).
**Referencia normativa revisada:** 24 de octubre de 2026.

Este documento propone preparación gradual; no acredita seis módulos
implementados, una certificación ni una ampliación aprobada del runtime.
La presencia de documentación, código o una PR no demuestra despliegue ni habilita actuación
autónoma. Se conservan la revisión humana y el proceso protegido existentes.

## Reutilización y prioridades

El [registro de capacidades](../../site/data/capability-registry.v1.json)
ya distingue estados, evidencia, superficie estática, ejecución en navegador,
servicio de producción y transporte externo. Debe seguir siendo la referencia;
no se propone otro inventario paralelo. Los campos adicionales siguientes son
candidatos para futuras revisiones acotadas, no cambios de esquema autorizados
por este documento.

| Prioridad y módulo | Preparar como documentación | Condición para ampliar |
| --- | --- | --- |
| Alta · Capacidades | Relacionar cada identificador existente con finalidad, responsable operativo, ejecución local/remota, proveedor y versión conocidos; conservar estados y límites de autoridad. Marcar lo desconocido. | Completar y revisar la ficha antes de habilitar una integración real. |
| Alta · Datos | Vincular capacidad y tratamiento al inventario de privacidad: categorías, localStorage, IndexedDB, cachés, destinatarios, conservación y alcance del borrado. | Revisar nuevos datos, transferencias o proveedores antes de activarlos. |
| Alta · Evidencia y revisión | Reutilizar procedencia, fuentes, incertidumbre y revisión humana existentes. Proponer referencias mínimas a versión, fecha y decisión de revisión. | Añadir trazabilidad específica cuando una capacidad real la necesite; sin registrar prompts ni conversaciones. |
| Alta · Cambios | Lista breve: finalidad, modelo, permisos, datos, autonomía, impacto, pruebas y reversión; enlazar issue, PR y aprobación aplicables. | Un cambio material abre revisión humana; la lista no concede permisos ni resuelve su clasificación jurídica. |
| Media · Incidentes | Plantilla mínima: identificador, fecha, capacidad, impacto, contención, responsable y referencia al canal privado verificado. Sin datos personales ni secretos en GitHub público. | Recepción persistente, alertas y seguimiento centralizado requieren backend y alcance propios. |
| Media · Transparencia | Preparar textos ES/EN/DE sobre intervención real de IA, límites y revisión disponible; vincular formación práctica a los roles y usos. | Mostrar avisos donde exista la función y registrar actividades formativas proporcionadas; sin controles decorativos ni certificados ficticios. |

## Referencias jurídicas condicionadas

- **Transparencia:** el [artículo 50](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50)
  se aplica desde el 2 de agosto de 2026. Distingue deberes del proveedor
  —interacción directa y marcado técnico de determinados contenidos— y del
  responsable del despliegue —determinados usos y publicaciones—. Hay
  excepciones específicas; por ejemplo, ciertos textos de interés público
  revisados por humanos con responsabilidad editorial. Un aviso genérico no
  satisface automáticamente todos esos deberes.
- **Alfabetización:** el [artículo 4](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-4)
  se aplica desde el 2 de febrero de 2025. Su versión modificada exige medidas
  de apoyo al desarrollo de competencias según personas y contexto, sin
  garantizar un nivel individual específico ni prescribir un certificado
  obligatorio.
- **Alto riesgo:** el [calendario oficial tras el AI Omnibus](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-113)
  fija las reglas del anexo III desde el
  2 de diciembre de 2027 y del anexo I desde el 2 de agosto de 2028.
  Estos calendarios dependen de clasificación y alcance; no abarcan toda IA.
- **Protección de datos:** una [EIPD/DPIA](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/obligations_en)
  procede cuando el tratamiento probablemente entrañe alto riesgo para
  derechos y libertades; no por usar IA en cualquier contexto.

La aplicabilidad requiere examinar función, finalidad, rol, datos y normativa
vigente. ECDS necesita una evaluación separada de datos sensibles y opiniones
políticas; esta preparación no valida anonimización ni habilita su tratamiento.

## Glosario, costes y límites

- **Sugerencia operativa:** mejora propuesta que necesita alcance y revisión;
  no equivale a obligación legal ni a función implementada.
- **Obligación condicionada:** deber aplicable si concurren sus presupuestos;
  su determinación corresponde a revisión humana competente.
- **Evidencia:** referencia comprobable dentro de su alcance; no certificación
  de verdad, cumplimiento o despliegue.

La documentación y el centro nativo inicial no requieren nuevas suscripciones
ni infraestructura. Un backend persistente de incidentes, proveedor generativo
o telemetría de red necesita otra issue, evaluación de datos y estimación de
desarrollo, operación y conservación. No se proponen cuadros de mando,
vigilancia, registros masivos ni determinaciones jurídicas automáticas.
