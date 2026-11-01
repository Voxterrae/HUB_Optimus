# AI Governance Review v0.1 — selección Web nativa

Registro técnico de 01/11/2026 conforme a la plantilla del repositorio. No ratifica una política, licencia, contrato o aprobación humana.

## 1. Propuesta y alcance exacto

Voxterrae/HUB_Optimus, #2021/#2040. Continúa el piloto 0b6662 e incorpora el padre 5ed8785; la PR registra externamente los SHAs completos del candidato y revisión después de publicar. El diff afecta únicamente `products/browser/windows`: configuración, launcher, guardado, interfaz nativa, pruebas, helper de diagnóstico y documentación. Los archivos preservados del padre se distinguen en el diff contra 5ed.

Implementación: elección explícita None/Mwmbl/SearXNG, migración compatible, bloqueo de fuente externa no confirmada y guardado transaccional. La fuente Mwmbl conserva su carácter de piloto privado. IA utilizada para implementar, probar, investigar condiciones y revisión técnica; no tiene autoridad de integración o aprobación. No se añade modelo generativo, crawler, acceso a datos del negocio, cuenta, pago o cambio de CI/contratos raíz.

## 2. Registro de seis capas

### Claim
Existe un selector nativo revisable conectado al host real y probado de forma portable. La aceptación posterior de Windows se registra por SHA; no se infiere cobertura mundial, buena relevancia o autorización comercial.

### Evidence
[Validación y comandos](VALIDATION_NATIVE_SEARCH_2026_11_01.md):195 comprobaciones C#,21 Python y compilaciones; RED→GREEN observados y fallos iniciales conservados. La ejecución nativa previa del padre tiene otro SHA. Los recibos de Windows del nuevo candidato y la revisión independiente se adjuntan externamente tras fijarlo.

### Inference
Los contratos probados aportan confianza a la configuración, persistencia y cancelación. Una GUI visible no implica controlador preparado; se conserva la comprobación real del padre. Un resultado de proveedor en Linux no demuestra automáticamente la ruta nativa de Windows.

### Uncertainty
Condiciones de acceso/resultados Mwmbl, cuota por IP, calidad, cobertura, SafeSearch e idiomas siguen sin resolver como oferta de uso diario. La ejecución del equipo físico, firma y tecnologías de apoyo requieren aceptación propia. Un proceso comprometido del mismo usuario queda fuera del aislamiento del perfil local.

### Narrative amplification
Los términos «propio», «privado», «gratuito» o «pruebas verdes» pueden confundirse con índice mundial, anonimato, capacidad ilimitada o aprobación humana. La interfaz identifica fuente y límites, y diferencia Índice offline de Web. No se transfieren pruebas históricas a un head nuevo por repetición.

### Operational relevance
Incremento medible y reversible en PR borrador, con consultas externas solo al solicitar búsqueda o el test opt-in. La condición comercial pendiente no se elimina mediante un checkbox o prueba técnica. Preparar una consulta al proveedor no equivale a enviarla.

## 3. Autoridad humana y permiso

La autoridad final y su comprobación corresponden a los registros de fundador/owner vigentes y el proceso protegido de GitHub. Un nombre o instrucción informal no reemplaza firma, identidad o decisión sobre el head. La decisión humana de integración, firma y uso empresarial está pendiente. No se modifica OWNER_AUTHORITY_HANDOFF.

El encargo permite preparar/probar el incremento y proponerlo en GitHub; no concede merge a main, derechos de terceros, pagos, cambios de permisos o envío de mensajes externos. La consulta de condiciones permanece como borrador para autorización específica de envío.

## 4. Capacidad, datos e impacto

Entradas: preferencia explícita, endpoint del operador y consulta voluntaria. Bearer permanece local; la fuente externa recibe consulta/conexión al buscar. No hay almacenamiento de consultas/resultados o uso de navegación privada como corpus. Los tests usan perfiles/VM desechables y consultas públicas acotadas. La captura posterior limpia la consulta del test y no retiene resultados.

Se mantienen TLS/HMAC/SPKI/nonce, Origin/Host y cierre confirmado solo del servicio propio. Una configuración independiente no verificable bloquea Web conservando Índice. Un guardado fallido devuelve el estado activo anterior; una identidad preparada con otra configuración no permite continuar.

Riesgos materiales: enviar a fuente equivocada, fallo de guardado, cierre no confirmado, cuota, contenido inadecuado, baja relevancia o licencia incompatible. Intervención: cancelar, elegir None, usar Índice, administrar por su propietario el servicio externo y retirar/revisar la propuesta. Los tests no certifican seguridad exhaustiva o cumplimiento jurídico.

## 5. Validación y reversibilidad

Comandos y límites en el registro enlazado. Windows se verifica mediante workflow existente desde main con source_commit explícito; la prueba de Internet es opt-in aparte. El candidato de QA, si se usa, cambia solo un switch del script diagnóstico y requiere comparación de fuentes de producción. No se suben perfiles, claves o un corpus de resultados.

Retirada: seleccionar None y cerrar solamente el host propio; o revertir el incremento por propuesta revisada. No hay migración destructiva o recurso de pago. Los ajustes anteriores se preservan cuando falla el guardado; una versión antigua no entiende la nueva preferencia y no debe tomarse como prueba de esta interfaz.

## 6. Disposición humana y handoff

Revisor humano/decisión/firma del head: pendientes. Revisión técnica independiente y pruebas posteriores se registran externamente; no constituyen autorización de merge. Siguen pendientes las condiciones empresariales del proveedor y la aceptación del equipo físico/accesibilidad.

AI_HANDOFF no cambia porque la propuesta sigue aislada y sin integrar; este módulo y #2021/#2040 contienen el handoff operativo. OWNER_AUTHORITY_HANDOFF conserva la autoridad vigente. No se reclaman propiedad, agencia, participación o derechos por la asistencia IA.
