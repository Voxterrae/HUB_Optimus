# Selección nativa de la fuente Web — #2021 / #2040

## Intención y decisiones delegadas
Continuar el encargo de gestionar la integración de búsqueda, verificar Windows y revisar condiciones externas. La conversación ya delegó los detalles técnicos y pidió ejecución directa; no se abre otra ronda de aprobación sobre el mismo alcance. Se reutilizan .NET10, WPF, el host y los controles existentes. Las decisiones siguientes son del implementador, no acuerdos nuevos atribuidos al usuario.

## Alternativas consideradas
Mantener CLI obliga a configurar manualmente cada perfil y no facilita el uso cotidiano. Activar Mwmbl por defecto transmite consultas sin elección y anticipa una aceptación comercial que no existe. Se elige un selector explícito en Privacidad y búsqueda: Web sin configurar / Mwmbl · piloto privado / SearXNG · servidor del operador. No se mezclan estos backends con la elección de navegación Google/DuckDuckGo/Optimus de la barra.

## Contrato
- Preferencia nullable WebProvider: ausente migra SearxEndpoint válido a SearXNG, y vacío a None. None explícito sigue desactivado aunque se recuerde un endpoint. Mwmbl no necesita URL/clave. SearXNG exige endpoint válido. Valores desconocidos fallan cerrado y conservan archivos dañados.
- Valor Core inmutable WebSearchConfiguration normalizado con None/Mwmbl/Searx. Construcción de argumentos mutuamente excluyentes; sin cambiar token, TLS, stdin privado o ejecutable incluido. Cambiar configuración detiene solo el host propio y confirma su salida antes de reiniciar.
- Un cambio invalida conexiones en preparación mediante revisión de configuración; no debe devolverse éxito de una elección anterior. Ninguna selección, carga o guardado envía consultas.
- El servicio independiente no revela su proveedor en el protocolo actual. Se conserva acceso a Index pero se rechaza Web de configuración no confirmada; se informa que otra instancia/servicio debe cerrarse o administrarse por su propietario. None tampoco transmite consultas Web.
- Guardado transaccional: si falla persistencia, se conservan las preferencias y política activas previas. El flujo existente cancela trabajo y deja los documentos inactivos antes de aplicar reglas. Una salida de host no confirmada bloquea su reconfiguración.
- Acceso directo «Elegir fuente Web» en Inicio y selector también disponible en los ajustes existentes. Selector con nombre accesible, controles44px, texto envolvente, teclado, tema y tamaño heredados. Campo endpoint solo para SearXNG. Mwmbl informa que recibe consulta/IP, tiene límites y sus condiciones empresariales/resultados siguen pendientes. Sin activación por defecto ni cuentas/tarjetas/pagos.
- Condiciones: preparar consulta concreta al contacto oficial; no enviar mensajes sin instrucción explícita de envío. Brave/Microsoft no se activan como sustitución: requieren otras condiciones/costes o integración distinta. Registrar fuentes actuales y límites sin certificación jurídica.

## Windows y aceptación
Base de trabajo: piloto0b6662 sobre46085be8, incorporando exactamente las pruebas/diagnósticos de padre07d13fe. El workflow protegido existente permite source_commit y gui sin cambios de CI. Primero suites/servicio empaquetado, después GUI. El fallo previo de GUI navegación no preparada exige evidencia: observar etapas de preparación y estado antes de decidir corrección; no forzar readiness ni debilitar privacidad. Si resulta un fallo real de preparación/entrada temprana, corregir la causa mediante regresión y conservar el primer fallo.

No se afirma licencia comercial resuelta, índice mundial, calidad general, accesibilidad certificada ni nueva descarga utilizable hasta verificar cada estado. Se conservan los límites del piloto y no se copian resultados al índice. Propuesta borrador y handoff trazable; sin merge a ramas compartidas o cambios de gobernanza/CI.
