# AI Governance Review v0.1 — Windows / Optimus Search 0.3

Registro técnico asistido por IA conforme a `templates/governance/AI_GOVERNANCE_REVIEW_v0.1.md`, referencia oficial leída en fcfb2468faf6b09a93539f9cac9313d28b6066e1. No constituye autorización, certificación legal, check CI ni aprobación humana. La jerarquía de fuentes y los registros de autoridad existentes siguen controlando; se conservan crédito y derechos de terceros.

## 1. Proposal and exact review scope

Repositorio Voxterrae/HUB_Optimus; coordinación #2021, propuesta Windows apilada sobre la importación #2018. Fecha UTC: 2026-10-30. Base original de contenido: `79c1d95d65e0f8b903039249cd8ce890b1ffe111`. Parent público actual: `1221bcd1ef53c8cd3d87496c36659164098602bb`, sustitución firmada con árbol idéntico verificado. La PR y el comentario externo posterior al último push registrarán el head completo efectivamente propuesto, su diff, evidencia y decisión humana; un resultado sobre otro head será histórico.

Objetivo único: servicio local común de búsqueda y su integración Windows. Archivos: `products/browser/search/**`, cambios puntuales de cliente/pruebas/versión/scripts/guías/avisos en `products/browser/windows/**` y notas fechadas en `products/browser/{README,VALIDATION}.md`. El manifiesto 0.3 y el diff de la PR enumeran las rutas exactas. No se modifican Linux, demo web, CI, Kernel, gobernanza raíz ni derechos. Las fuentes 0.2 y sus hashes históricos no se reescriben como si fueran 0.3.

Implementado: catálogo finito BM25 e importación explícita, conector SearXNG, selector Web/Índice/Wikipedia, cancelación y gestión exclusiva del proceso iniciado por Windows. La corrección final autentica cada transporte local con TLS y alinea validación, rutas y errores upstream. Su head público y pruebas se registran externamente. No hay buscador mundial independiente, IA generativa nativa, IoT ni despliegue cloud. La IA se usa para implementación, pruebas, revisión y este registro; carece de autoridad de aceptación o merge.

## 2. Six-layer analytical record

### Claim

La afirmación acotada es que existe una implementación revisable de búsqueda en catálogo propio y conexión a un agregador web, con límites y fallos explícitos, más una distribución Windows alpha reproducible. El registro no afirma aceptación general de Internet, ejecución Windows, accesibilidad certificada o aprobación humana.

### Evidence

En el head local 70e1438 se ejecutaron 124 comprobaciones C# (35 Core, 37 Search Windows, 24 Privacy y 28 backend), 13 pruebas Python y compilación WPF sin errores/advertencias. Son evidencia anterior a las correcciones. En la integración local 78242d7 se ejecutaron después 145 comprobaciones C# (35 Core, 47 Search Windows, 24 Privacy, 39 backend), 13 Python y WPF sin errores/advertencias; el registro externo vincula estos bytes al SHA público. Las pruebas nuevas usan TLS real e incluyen sustitución de listener, reconexión, certificados erróneos y cancelación sin revelar consulta/token. Las pruebas reales incluyen HTTP/stream/procesos e importación atómica; los PE sintéticos del empaquetador nunca se ejecutan. El CLI real importó las tres ayudas originales incluidas. Se publicaron ambos apphosts autocontenidos Windows x64 con .NET 10.0.14. La comprobación real reveló un falso positivo en dos nombres de DLL oficiales; su corrección permite solo las dos rutas y SHA-256 exactos, con 18 pruebas Python y verificación real del directorio publicado. Las DLL coinciden byte por byte con el paquete oficial restaurado; no se relaja el rechazo de fuentes/perfiles/secretos. Código C# sin cambios desde los 145 checks; la entrega definitiva requiere reconstrucción del head final.

Avisos ASP.NET conservados byte por byte desde https://github.com/dotnet/aspnetcore/tree/v10.0.14; URLs y SHA-256 en `windows/docs/third-party/ASPNetCore.PROVENANCE.md`. SearXNG oficial se instaló desde el commit `ffa88e3ba3ade64185d5754c839cdf5a80708c4a`, únicamente para QA temporal. Evidencia contradictoria material: Google denegado, DDG CAPTCHA, Brave 429, Bing irrelevante/vacío. No hubo aceptación web relevante ni bypass. Los logs de QA no se distribuyen ni contienen datos de negocio.

### Inference

Los tests y la publicación aportan confianza sobre comportamiento y estructura dentro de los casos observados. La separación del host permite reutilizar el contrato desde Linux; no prueba una integración Linux existente. Arrancar SearXNG o recibir JSON no implica obtener resultados útiles. Tres ayudas de Optimus demuestran un índice real de alcance limitado, sin acreditar cobertura externa.

### Uncertainty

Pendientes: aceptación en Windows físico, tecnologías de apoyo, comportamiento WebView2/COM, PowerShell, firma, relevancia web y proveedor estable. Los controles estructurales/hash no certifican exhaustivamente el runtime ni el cumplimiento legal. El token y TLS local no protegen de un proceso comprometido del mismo usuario o un administrador. La revisión anterior encontró que un nonce de estado aislado no cubría la sustitución del listener entre conexiones; la corrección TLS y su evidencia constan en el incremento final. El certificado vive en memoria y vence a los 30 días: hosts independientes de larga duración deben reiniciarse para renovarlo; se rechaza la conexión al vencer.

### Narrative amplification

Riesgos: presentar compilación Linux, fixtures, respuesta vacía, arranque del agregador o lenguaje de «protección» como aceptación de producto; repetir resultados históricos para un head nuevo; convertir revisión IA en decisión humana. Este registro mantiene separados esos estados y conserva evidencia adversa. La urgencia de entregar no elimina verificaciones ni límites.

### Operational relevance

Acción acotada: propuesta en PR borrador y paquete privado sin firma, con hashes y límites verificables. El siguiente hito es una consulta web relevante y aceptación Windows. El fallo upstream no justifica contratar proveedores, crear cuentas, eludir restricciones o ampliar permisos. No se activa Azure/Dataverse ni otros sistemas por documentar la arquitectura.

## 3. Human authority and permission boundary

Autoridad final: Benjamin Gerrit Hoff conforme a Founder Ownership and Authority Charter, owner identity manifest y OWNER_AUTHORITY_HANDOFF vigentes. Su nombre o un checkbox no prueban autorización. Decisión humana, firma e identidad requerida para el head final: **pendientes**, según el proceso protegido aplicable y con referencia externa posterior al último push.

Delegación de trabajo: preparar, verificar y proponer este incremento Windows dentro de #2021; ramas aisladas y revisión técnica asistida. Termina con el handoff o revocación; revertir la propuesta retira el cambio. No concede merge, administración, acceso adicional a datos/cuentas, despliegue público, pagos, cambios de CI/Kernel/derechos ni autoridad independiente a colaboradores o IA. Una PR borrador y un paquete privado no sustituyen las autorizaciones separadas de operaciones posteriores.

## 4. Capability, data, and impact boundary

Entradas: consulta enviada expresamente, marcadores permitidos, catálogo público/autorizado, configuración del operador y token de perfil. Salidas: resultados remotos o de catálogo finito, etiquetas de fuente y errores saneados. La ayuda incluida es contenido original, tres documentos etiquetados Ayuda Optimus; sus fechas indican versión, sin afirmar una descarga remota. No se ingieren documentos del negocio, datos privados o historial.

Fronteras exigidas: loopback IPv4, identidad del transporte ligada al token, Bearer solo local, rechazo Origin/Host ajenos, sin CORS ni log de consultas, upstream fijo sin cookies/redirecciones/credenciales ambientales, límites y cancelación. Importación atómica, sin crawler/historial/caché. Wikipedia explícita; Windows detiene únicamente su propio proceso. Tokens y claves privadas no entran en Git, argumentos o ZIP.

Fallos materiales: fuga de consultas/token, URL insegura, fallo upstream presentado como ausencia de resultados, proceso ajeno detenido, catálogo parcial, paquete incompleto o interfaz inaccesible. Intervención humana: cancelar, elegir fuente, configurar/parar servicio propio, retirar el ZIP y controlar el perfil. No cambia contratos, derechos o autoridad ni habilita usos sensibles; cualquier cambio requiere su proceso separado.

## 5. Validation and reversibility

Comandos y límites en VALIDATION.md. Se separa evidencia pre-revisión de los resultados finales del head externo. Scripts PowerShell y producto Windows no ejecutados aquí. Los binarios reales se publican para win-x64; PE, runtimeconfig, corpus obligatorio, avisos, CRC y hashes completos se comprueban sin fingir ejecución de esos PE. El manifiesto 0.3 identifica fuentes; no convierte metadata declarada en prueba de funcionamiento.

Reversión: retirar el ZIP alpha y revertir commits del módulo mediante una propuesta revisada; restaurar desde Git sin sobrescribir la procedencia 0.2. Detener solo procesos propios. No hay migración destructiva, recurso de pago ni despliegue habilitado por esta tarea. La retirada/publicación en otras plataformas conserva sus permisos aplicables.

## 6. Human review disposition

Revisor humano, head completo y decisión: **pendientes**, con registro externo en la PR/comentario después del último push. La revisión técnica de IA y pruebas no cuentan como aprobación humana. Quedan bloqueadas la aceptación web relevante y la aceptación Windows/accesibilidad/firma; cualquier objeción de la revisión final se conserva con su disposición.

Siguiente acción dentro del encargo: preparar PR borrador Related to #2021 y handoff con límites y artefacto privado. Sin merge, despliegue ni cambios de permisos. `docs/context/AI_HANDOFF.md` permanece sin modificar porque es una propuesta aislada y aún no integrada; el handoff del producto queda en la documentación del módulo y #2021. OWNER_AUTHORITY_HANDOFF no cambia porque no se alteran autoridad, titularidad o controles de colaboración.
