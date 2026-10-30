# Decisiones del incremento Windows — #2021

Registro de decisiones técnicas tomadas durante la ejecución delegada. Son reversibles y no constituyen aprobación humana del head, firma, merge ni despliegue. Se mantiene la coordinación Linux en #2021 y la autoría de cada aportación.

| Orden | Decisión y motivo | Coste si hubiera que cambiarla |
| --- | --- | --- |
| 1 | Ejecutar el incremento Windows descrito en #2021 con la delegación y el «adelante» existentes. | Rehacer código o interfaz de la propuesta; sin gasto contratado. |
| 2 | Reutilizar .NET 10 para el servicio, evitando otro runtime de desarrollo. | Huella de runtime y adaptación de futuros clientes en otros lenguajes. |
| 3 | Dividir tareas independientes en ramas aisladas y un contrato común; integrar secuencialmente. | Rehacer una integración si los contratos divergen. |
| 4 | Usar briefs y paquetes de diff manuales al no estar disponibles los scripts de coordinación. | Reconstrucción manual de la trazabilidad. |
| 5 | Fijar el marcador de estado como nombre OptimusSearch y versión 1. | Actualizar juntos protocolo y clientes. |
| 6 | Incluir tres ayudas originales y claramente etiquetadas como corpus finito inicial del índice propio. | Retirar ese corpus y reconstruir el paquete. No equivale a cobertura web. |
| 7 | Cambiar únicamente Version del proyecto App a 0.3 porque el valor literal anterior prevalecía sobre las propiedades comunes. | Rehacer metadatos de versión. |
| 8 | Añadir una prueba HMAC de token, nonce y puerto antes de entregar una conexión autenticada. | Actualizar servicios locales anteriores. La revisión posterior demostró que esta prueba aislada no cubría el cambio de listener entre conexiones. |
| 9 | Exigir TLS local con certificado efímero autenticado por el token para cada conexión real; mantener las claves de certificado solo en memoria y prohibir fallback HTTP. | Cambio del protocolo alpha y mayor superficie de pruebas/documentación. Corrige la carrera que quedaba tras la comprobación de estado. |

| 10 | Aceptar para esta alpha el certificado efímero de 30 días, con reinicio explícito de los hosts independientes que superen ese plazo. El host iniciado por el navegador normalmente dura lo mismo que la sesión. | Reinicio operativo o nueva implementación de renovación para un servicio permanente. El vencimiento falla cerrado. |

Las cuatro limitaciones que requieren evidencia posterior son: resultados web generales relevantes, ejecución en Windows físico, accesibilidad con tecnologías de apoyo y firma de distribución. No se convierten en resultados positivos por compilar o pasar fixtures. La prueba de proveedores no justifica eludir sus restricciones ni contratar recursos.
