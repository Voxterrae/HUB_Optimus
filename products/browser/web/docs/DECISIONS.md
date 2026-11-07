# Decisiones de implementación y coste de revisión

Decisiones tomadas dentro del piloto delegado. No asignan derechos, cambian autoridad ni autorizan gasto. La decisión de integración sigue en la propuesta protegida de GitHub.

| Decisión | Motivo | Coste si hubiera que cambiarla |
|---|---|---|
| Continuar el piloto ya aprobado sin repetir su aprobación de diseño | Se delegaron los detalles de implementación | Rehacer parte de la interfaz; no existe compromiso de gasto |
| Añadir un host web sin dependencias y preservar la demo React | Entregar un módulo ejecutable pequeño y portable | Trabajo adicional si se integra después en componentes React |
| Registrar briefs, revisiones y decisiones mediante archivos y diffs Git | Los scripts de coordinación indicados por el skill no estaban disponibles | Reconstruir trazabilidad si el registro manual fuese insuficiente |
| Implementar módulos independientes en worktrees separados | Trabajar en paralelo sin sobrescribir archivos compartidos | Corregir interfaces al integrar |
| Usar voz solo local y conservar entrada escrita | La persona controla cuándo se usa voz y no hay alternativa remota silenciosa | Menos dispositivos pueden dictar en este piloto |
| Tratar el máximo de120 del título de respaldo como contrato obligatorio | Un URL largo no debe saltarse el límite por faltar título | Etiquetas largas truncadas, manteniendo el URL completo permitido |
| Completar Borrar datos para descartar también el nuevo borrador de sesión | El texto pendiente no debe reaparecer después de esa acción explícita | Se pierde ese texto sin guardar al elegir Borrar datos |

La revisión técnica detectó y cerró problemas de reentrancia de voz, foco/modal, límites, borradores y limpieza de respuestas rechazadas. El seguimiento de los hallazgos corresponde al head actual de la PR. Micrófono, móviles físicos, lectores de pantalla, traducción nativa y zoom real200% conservan el estado de aceptación pendiente descrito en VALIDATION.md. Los idiomas de voz e interfaz se eligen por separado; el texto de la ayuda hablada se traduce al idioma de voz seleccionado, mientras los textos visibles conservan el idioma de interfaz.
