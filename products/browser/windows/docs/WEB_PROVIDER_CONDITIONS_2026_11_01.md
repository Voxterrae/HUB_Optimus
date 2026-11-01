# Condiciones del proveedor Web — revisión 01/11/2026

Objetivo: decidir una fuente viable para uso cotidiano de Optimus, preservando elección, privacidad y control de costes. Esta revisión documental no certifica una licencia ni cambia los derechos del proyecto. La implementación nativa no equivale a aceptación comercial del proveedor.

| Fuente | Publicación oficial observada | Decisión de este incremento |
| --- | --- | --- |
| Mwmbl | Portada: acceso anónimo sin cuenta/clave,1000 consultas/mes/IP y 1/s. Términos: cláusula general de cuenta/clave, aplicaciones comerciales permitidas y resultados bajo CC BY-NC-SA 4.0. | Piloto privado explícito; solicitar aclaración escrita sobre acceso y resultados antes del uso empresarial. No crear corpus/importar resultados. |
| Brave Search API | Crédito mensual $5 y precio $5/1000 solicitudes; registro, clave y tarjeta para todos los planes, con posible retención de verificación. Sus términos contemplan interfaces de búsqueda para personas y almacenamiento operativo transitorio, no caché/base persistente o reventa. | Candidato si se autoriza separadamente cuenta/tarjeta y se valida el control de gasto y retención. No se activa en este trabajo. |
| Microsoft | Bing Search APIs retiradas el 11/08/2025. Grounding with Bing es una integración distinta, de pago, sin resultados brutos como API genérica para este navegador. | No tratarlo como sustituto gratuito/directo de la fuente Web. No crear recursos Azure o suscripciones para resolver este piloto. |

Fuentes primarias consultadas:

- https://developer.mwmbl.org/
- https://developer.mwmbl.org/terms/
- https://api-dashboard.search.brave.com/documentation/pricing
- https://api-dashboard.search.brave.com/documentation/resources/help-feedback
- https://api-dashboard.search.brave.com/documentation/resources/terms-of-service
- https://api-dashboard.search.brave.com/documentation/services/web-search
- https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement
- https://www.microsoft.com/en-us/bing/apis

La distinción entre acceso comercial a una API y derechos sobre sus resultados requiere aclaración del proveedor. No se infiere autorización comercial de una respuesta HTTP 200 ni de que exista un plan gratuito. La licencia de las páginas originales conserva su propio alcance. Las condiciones y precios pueden cambiar; revisar de nuevo antes de activar otro plan o uso.

## Consulta preparada — no enviada

Destinatario publicado en los términos: info@mwmbl.org. No se ha contactado con el proveedor ni aceptado un acuerdo. La autorización de desarrollo no se convierte en envío de mensajes externos.

Subject: Clarification of anonymous API access and commercial display of search results

Hello Mwmbl team,

We are evaluating Mwmbl for the search interface of our Optimus browser. We would like to start within the anonymous allowance, without registering a payment method.

Your API page describes anonymous access, while the Terms contain a general account/API-key requirement. The Terms also allow commercial applications but place search results under CC BY-NC-SA 4.0. Before enabling this for a small company's daily use, could you confirm:

1. Whether anonymous access is permitted for a company within the published IP quota.
2. Whether displaying titles, URLs and snippets to employees or customers is permitted commercially, and which licence governs that use.
3. The requirements for attribution, transient caching, retention and inclusion of snippets in AI-assisted answers.
4. Whether the monthly allowance is shared by outgoing IP and whether exceeding it only blocks requests without activating billing.

A written clarification, or updated terms resolving these points, would help us select an appropriate integration.

Thank you.

## Estado operativo

Respuesta del proveedor: pendiente; consulta sin enviar. Mwmbl permanece opcional y etiquetado como piloto privado. La selección nativa, los tests y las compilaciones no cierran esta decisión. No se añade vigilancia automática de correo ni se transfieren consultas, perfiles o datos del negocio como parte de esta revisión.
