# AI Governance Review v0.1 — piloto Web Mwmbl

Registro del 01/11/2026 conforme a [la plantilla vigente](../../../../templates/governance/AI_GOVERNANCE_REVIEW_v0.1.md). Es evidencia técnica de una propuesta, no autorización, certificación legal ni aprobación humana. No modifica las reglas de autoridad o derechos del proyecto.

## 1. Propuesta y alcance exacto

Voxterrae/HUB_Optimus, coordinación #2021, PR borrador apilada sobre #2034. Base final `46085be8dec5676271290eb3e2906546fc7efd77`. La PR y el comentario posterior en #2021 registran externamente el head completo, diff, verificación y estado de revisión después del último push; este archivo no contiene un SHA autorreferente.

Capacidad implementada: selección CLI explícita de un conector de resultados Web externos y tratamiento visible de cuota. Su implementación y tres consultas Linux constan en [VALIDATION_MWMBL_PILOT.md](VALIDATION_MWMBL_PILOT.md). No se activa como defecto ni se despliega como servicio permanente. No se añaden IA generativa, crawler, nuevos permisos, pagos, cuentas o integración Windows automática.

Archivos afectados, todos dentro de `products/browser/`:

- `search/README.md`, `search/docs/PROTOCOL.md`, `search/docs/VALIDATION_MWMBL_PILOT.md` y este registro.
- `search/docs/superpowers/specs/2026-11-01-mwmbl-pilot-design.md` y `search/docs/superpowers/plans/2026-11-01-mwmbl-pilot.md`.
- `search/src/Optimus.Search/{IWebSearchProvider,MwmblSearchProvider,Program,SearchServer,SearxSearchProvider}.cs`.
- `search/tests/Optimus.Search.Tests/{Program,MwmblPilotTests,MwmblProviderTests}.cs`.
- `windows/src/Optimus.Core/SearchService.cs` y `windows/tests/Optimus.Search.Tests/Program.cs`.

Asistencia IA: implementación, pruebas, investigación documental y revisión independiente del diff. No atribuye autoridad de aprobación o merge a esos agentes. La especificación y el plan describen el piloto; no constituyen una modificación del roadmap o los contratos raíz.

## 2. Registro analítico de seis capas

### Claim

La afirmación acotada es que Optimus puede devolver resultados Web mediante este conector opcional. No se afirma índice mundial propio, excelente relevancia, funcionamiento del navegador Windows ni disponibilidad comercial.

### Evidence

El registro de validación separa fixtures, pruebas de proceso/TLS y tres consultas reales el 01/11/2026 a las17:07 UTC, cada una con HTTP 200 y 20 enlaces. Se utilizó el transporte de producción; no se publicó un dataset de resultados. El head público se vincula externamente tras el push. La documentación oficial de [acceso](https://developer.mwmbl.org/) y [condiciones](https://developer.mwmbl.org/terms/) se consultó el mismo día. Las condiciones contienen discrepancias: cuenta/clave general frente a modalidad anónima, y aplicaciones comerciales frente a resultados CC BY-NC-SA 4.0. Ninguna respuesta 200 resuelve esas discrepancias.

### Inference

La observación acredita tránsito real de consultas por Optimus hasta una fuente externa en este entorno. No demuestra operación estable, calidad general ni aceptación de otras plataformas. La rapidez de dos consultas puede deberse a caché externa; no se infiere latencia garantizada.

### Uncertainty

Persisten condiciones/licencia de producción, cuota por IP compartida, SLA inexistente, relevancia, cobertura, idiomas, SafeSearch, Windows/GUI y accesibilidad real. La consulta `linux` incluyó un carrito de compra. No se han visitado ni certificado como seguros los destinos devueltos. La contradicción documental mantiene pendiente la aceptación comercial y reutilización de resultados.

### Narrative amplification

«Buscador propio», «privado», «gratis» o una batería verde podrían confundirse con cobertura mundial, anonimato de red, capacidad ilimitada o aprobación humana. El piloto identifica Mwmbl como fuente externa, comunica que recibe consulta/IP y no promete esas propiedades. Las observaciones adversas y verificaciones pendientes se conservan.

### Operational relevance

Proponer una PR borrador medible y reversible permite revisar el adaptador. No habilita un despliegue comercial ni justifica activar pagos, nuevas claves, infraestructura o servicios públicos. La selección de proveedor es explícita y los errores no se convierten en resultados de otra fuente.

## 3. Autoridad humana y permisos

La autoridad final corresponde a Benjamin Gerrit Hoff según Founder Ownership and Authority Charter, owner identity manifest y OWNER_AUTHORITY_HANDOFF vigentes. Un nombre, petición en chat, credencial técnica o checkbox no sustituye el proceso protegido. La decisión humana sobre el head propuesto está **pendiente**, al igual que firma y revisión exigibles para su integración. La revisión IA no la reemplaza.

El encargo técnico permite preparar y verificar una propuesta de búsqueda en #2021 y hacer consultas públicas benignas, finitas, sin crear cuentas ni facturación. La delegación termina con el handoff o revocación y permite retirar la propuesta. No concede merge, cambios de gobernanza, derechos, CI, permisos, acceso a perfiles del usuario o datos del negocio. Cualquier despliegue, uso sensible o habilitación comercial conserva sus decisiones y controles separados.

## 4. Capacidad, datos e impacto

Entradas: consulta explícita del usuario y token de perfil que permanece local. Salidas: enlaces/textos externos saneados con procedencia y errores genéricos. La petición externa fija solo envía `q`, Accept y User-Agent; no el bearer, cookies o credenciales ambientales. Mwmbl y la red de salida reciben los datos necesarios para atenderla. No se implementa retención de consultas, caché, crawling o importación de sus resultados al índice.

Se conservan TLS/HMAC/SPKI, bearer, nonce, loopback, Origin/Host, ausencia de CORS y límites del servicio. `scope=index` sigue sin red. Un proceso comprometido del mismo usuario o administrador conserva capacidades fuera de este aislamiento. La coordinación de 1,1 s es por proceso; no administra la cuota compartida por IP.

Fallos materiales: fuga de consulta/token, agotamiento de cuota, contenido inadecuado, origen mal atribuido, baja relevancia, timeout o uso de resultados con condiciones incompatibles. Intervención humana: cancelar, retirar la opción CLI, parar únicamente el host propio y revisar la propuesta. No se modifican contratos, derechos o permisos para resolver esas limitaciones.

## 5. Validación y reversibilidad

Comandos, resultados y límites en el registro del piloto. Se conserva la distinción entre pruebas Linux y ejecución Windows; las verificaciones CNG nativas no se ejecutan en este entorno. No hay nueva distribución binaria, firma, despliegue o aceptación de tecnologías de apoyo. Las tres consultas usaron un host efímero que se cerró al terminar.

Reversión: omitir `--web-provider mwmbl` y cerrar el host propio de prueba; o revertir este incremento mediante propuesta revisada. El índice y SearXNG anteriores conservan su funcionamiento. No hay migración destructiva, recursos de pago ni permisos adicionales que retirar. Una operación externa posterior necesitará su propio alcance y autorización.

## 6. Disposición de revisión humana

Revisor humano, decisión, firma y aceptación del head final: **pendientes**, con referencia externa en la PR/#2021. Objecciones abiertas: condiciones de acceso/resultados, calidad y cobertura, integración y ejecución Windows, accesibilidad y operación permanente. La revisión técnica independiente se incorpora al registro de validación y no cierra estas decisiones humanas.

Siguiente acción técnica: publicar propuesta borrador y evidencia acotada, sin merge ni despliegue. `docs/context/AI_HANDOFF.md` no se modifica porque el incremento no está integrado y el handoff del módulo queda en esta documentación y #2021. `OWNER_AUTHORITY_HANDOFF.md` conserva el estado vigente; no se alteran autoridad, titularidad o controles de colaboración.
