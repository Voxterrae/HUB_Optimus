# Optimus Search — piloto Web explícito Mwmbl

## Alcance
Continuar el encargo de #2021 de hacer funcionar búsqueda Web real, con detalles técnicos delegados por el usuario. Reutilizar el host .NET10 y su protocolo HTTPS local. Base fija 46085be8dec5676271290eb3e2906546fc7efd77 (#2034), sin duplicar la corrección nativa en curso. Sin nuevas cuentas, claves, pagos, infraestructura, cambios de CI o fusión.

## Enfoques y decisión técnica del implementador
SearXNG controlado permanece disponible, pero su aceptación Web histórica está bloqueada por upstream. Crecer el índice Optimus es útil y finito; no resuelve cobertura Web general. Elegimos un adaptador piloto Mwmbl explícito porque tres lecturas HTTPS reales hoy devolvieron enlaces (web accessibility40, accesibilidad web57, linux122). Es fuente externa, no índice propio ni aceptación de Windows. No se modifica la política conservadora de resultados parciales SearXNG.

## Contrato
- CLI optin `--web-provider mwmbl`, incompatible con `--searx-url`; valores desconocidos o repetidos fallan. Sin opción, comportamiento anterior intacto. El launcher/configuración nativa no activa Mwmbl automáticamente.
- Interfaz interna compartida `IWebSearchProvider : IDisposable` con SearchAsync(query,language,CancellationToken). SearXNG conserva su comportamiento.
- Mwmbl usa exclusivamente HTTPS `https://api.mwmbl.org/api/v2/search/?q=...`, sin clave, cookies, credenciales ambientales HTTP ni redirecciones. La consulta se transmite al proveedor solo al buscar. No hay reintento ni fallback.
- JSON objeto/results obligatorio; error no nulo o esquema inválido falla. Tamaño1MiB, profundidad32, plazo10s incluyendo espera, headers y cuerpo. Token local nunca se añade a la petición externa.
- Máximo20 resultados válidos, orden original, URLs normalizadas/deduplicadas, títulos240 y contenido1200. Conservar procedencia: Mwmbl + engine del proveedor identificado mediante nombres conocidos (índice/comunidad/Wikipedia/Google) o indicar origen no especificado.
- Separación mínima de1.1s entre inicios externos, compartida por instancias del proceso, sin cola no cancelable. La cuota por IP/procesos externos es del proveedor, no una garantía local. HTTP429 devuelve429/upstream-rate-limited con mensaje genérico y ningún resultado externo; Windows presenta un mensaje claro. No evasión de cuotas.
- Protocolo v1 y TLS/HMAC/SPKI, nonce, token, Origin/Host y límites index quedan intactos. scope=index no consulta la red.
- La API no garantiza idioma, SafeSearch, relevancia, disponibilidad ni cobertura total. No se instala como proveedor predeterminado ni se afirma protección de contenidos del proveedor.

## Aceptación y límites
Pruebas de CLI, parser/filtrado/procedencia, error/redirect/429, streaming/cancelación y separación de solicitudes; regresiones existentes y compilaciones. Prueba separada, benigna y acotada: cliente de producción TLS autenticado → API Optimus → adaptador real → Mwmbl → enlaces. No usar fixtures como prueba de Internet. Registrar SHA/fuentes, consultas, tiempos y resultados; sin guardar bearer o datos privados. Windows/GUI y despliegue permanente siguen pendientes.

## Fuentes verificadas 01/11/2026
https://developer.mwmbl.org/ documenta modalidad anónima1000consultas/mes a1/s por IP, sin clave/tarjeta, y https://developer.mwmbl.org/terms/ publica límites y servicio sin SLA. No se activa facturación ni plan identificado. Si cambian sus condiciones o se agota cuota, el piloto puede dejar de responder; el usuario conserva la elección de proveedor. Licencias/condiciones externas no alteran derechos del proyecto.
