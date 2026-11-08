# Optimus Search: índice propio y Web explícita con Brave

Fecha: 2026-11-07. Estado: propuesta para revisión; no implementada ni activada.
Base inspeccionada: main `0a1dde5c47be9076973478cfb568a2a8219c3fdb`.

## Intención y decisión de producto

Mantener «Tu índice» como búsqueda propia de Optimus y añadir «Web · Brave»
como elección explícita para buscar en Internet. El usuario aceptó avanzar con
esta vía híbrida tras comparar control, cobertura y coste. Esa aceptación de
dirección no equivale a aprobación de este diseño, integración protegida,
suscripción, gasto ni despliegue.

El objetivo es ofrecer búsqueda útil sin presentar un índice de terceros como
propio. Las consultas de «Tu índice» no se envían al proveedor Web. No hay
fallback automático, envío al escribir, autocompletado remoto ni consulta
simultánea a ambos motores.

## Enfoques considerados

| Enfoque | Ventaja | Coste o limitación |
| --- | --- | --- |
| Solo índice propio | Control del catálogo y procesamiento | Cobertura limitada y mantenimiento continuo |
| Índice propio + API Brave | Catálogo controlado y búsqueda general explícita | Dependencia externa, condiciones y coste por uso |

Se eligió la vía híbrida. No se propone construir un índice de toda Internet
ni emplear scraping de portales para sustituir la API.

## Estado actual y límites de compatibilidad

En la base inspeccionada, SearchServer acepta concretamente SearxSearchProvider;
este consume JSON SearXNG y etiqueta resultados como SearXNG. SearchHost usa
HTTPS local, prueba nonce/HMAC y token de perfil, con endpoint local fijo.
No debe cambiarse el origen ni falsificarse esa procedencia para conectar Brave.

La PR #2098 propone un servicio remoto independiente para un catálogo finito.
Su contrato de catálogo verificado no representa búsqueda Web y no se reutiliza
como si fuera un endpoint SearXNG. La PR #2107 es una corrección local del plazo
de health y conserva su alcance. Ninguna de esas PR se integra por este diseño.

La aceptación Mwmbl/SearXNG de #2062 sigue bloqueada: no se modifica su fuente
fijada, criterio, workflow ni historia. Las nuevas pruebas Brave serán un alcance
separado. El informe anterior no permite reconstruir las URLs originales.

## Componentes propuestos

Primero, una biblioteca C# net10.0 independiente con adaptador Brave, modelos y
pruebas sin red externa. No se conecta a Program, SearchServer, WPF ni a un
workflow. Esta primera entrega deja intactos los contratos existentes y evita
tener que aprobar de golpe todo el servicio.

Después, un gateway servidor propio, preferentemente en Azure, como proceso
separado del servicio de catálogo finito. Mantiene la clave Brave solo en un
secreto montado en servidor. Nunca en código, argumentos de proceso, binario
Windows, configuración pública, repositorio, resultados o informes.

El cliente nativo llama al gateway mediante HTTPS y una credencial remota
revocable distinta del token local. El gateway autentica antes de reservar cuota
y llamar a Brave. No se publica como proxy anónimo. Se conserva íntegra la
frontera local HTTPS/HMAC; una futura extensión de configuración y cliente se
propone en su propia PR, con protocolo explícito y pruebas de credenciales.
No se presupone que ese soporte exista hoy.

La separación de biblioteca, gateway y cliente es una decisión técnica propuesta
por el implementador, no una infraestructura ya autorizada o disponible.

## Contrato del adaptador

- Destino de producción fijo y HTTPS, verificado contra documentación oficial
  al implementar. Sin endpoint arbitrario aportado por el navegador.
- Token únicamente en cabecera x-subscription-token. Sin cookies, credenciales
  de sistema, redirecciones ni proxy del sistema en el cliente HTTP.
- Consulta validada antes de enviar: máximo 500 caracteres y 75 palabras,
  sin controles. Idiomas admitidos ES, CA, EN, DE, FR y RU, con mapeo explícito
  a códigos soportados por Brave. Código no soportado: error local.
- Solo resultados Web, máximo 20, safesearch=strict y texto sin decoraciones.
  Nada de imágenes, respuestas IA, resúmenes generados ni callbacks.
- Una solicitud por acción confirmada. Sin reintentos automáticos, paginación,
  fallback ni rotación de proveedor, clave o identidad.
- Plazo máximo propuesto de 10 segundos, cancelación propagada, cuerpo de
  respuesta máximo 1 MiB y profundidad JSON máxima 32.
- Parsear exclusivamente resultados Web. Validar y deduplicar URLs; rechazar
  esquemas distintos de HTTP/HTTPS, credenciales, controles y URLs malformadas.
  Mostrar título y extracto como texto, nunca HTML ejecutable.
- Procedencia «Brave» en cada resultado; no mezclar procedencias ni atribuir
  integridad del catálogo propio a resultados de Internet.
- Respuesta vacía válida se distingue de error de autenticación, límite, plazo,
  transporte o formato. Fallos se comunican sin cuerpo ni URI del proveedor.
- El filtrado estricto es una petición al proveedor, no una garantía de
  protección absoluta. El bloqueo de navegación y la política familiar son
  controles separados y no se acreditan con estas pruebas.

## Privacidad, derechos y presupuesto

La elección Web debe informar antes del primer envío que la consulta sale a
nuestro servidor y a Brave. No se envían historial, marcadores, documentos
privados ni identidad del usuario al proveedor como parámetros adicionales.
Brave seguirá recibiendo la consulta y la conexión desde el servidor.

La documentación consultada prohíbe retener datos recibidos de la API salvo
acuerdo aplicable. Por defecto no habrá caché persistente, telemetría de
consultas, volcados HTTP, resultados en CI, exportación ni incorporación al
índice propio o a memoria de claims. Los tests offline usan fixtures sintéticos,
no respuestas reales copiadas. La revisión previa a activación debe confirmar
que el plan permite el uso y la visualización transitoria propuestos.

Los diagnósticos del gateway y de su plataforma deben excluir consultas,
cabeceras, cuerpos y URLs completas; solo códigos propios, duración y contadores.
El cliente mantendrá resultados solo durante la vista activa y descartará su
modelo al cerrarla o sustituir la búsqueda. No se promete borrado forense de RAM
ni ausencia de tratamiento por plataformas externas.

Piloto propuesto: invitación privada, hasta 100 intentos de salida, concurrencia
global 1, una sola instancia y una sola clave de uso exclusivo. Reservar cada
intento atómicamente antes del envío; intentos fallidos o inciertos también
consumen el cupo y no se reembolsan automáticamente. Contador duradero que
sobrevive reinicios; si no puede verificarse, bloquear llamadas. No es un
contador solo en memoria ni un límite por réplica.

La tarifa observada de 5 USD por 1.000 solicitudes da 0,50 USD por 100 solicitudes
antes de créditos e impuestos; Azure se calcula aparte. Este cálculo no es un
techo monetario contractual. Previamente a activación: verificar tarifa, plan,
saldo/límite de proveedor, recarga automática desactivada, coste de Azure y
artefacto exacto. No se crea cuenta, acepta facturación, compra crédito, registra
proveedores Azure ni despliega con este documento.

## Entregas y aceptación

1. Adaptador aislado y pruebas offline: desactivado, sin registro en runtime,
   sin secretos reales y sin solicitudes externas. Probar parámetros estrictos,
   validación previa, procedencia, resultado vacío, JSON inválido, duplicados,
   HTML como texto, bytes/plazo/cancelación, rechazo de redirecciones y errores.
   Demostrar con transporte controlado que no hay reintentos ni fuga de clave.
2. Gateway y protocolo versionado en PR separada: autenticación revocable,
   admisión, contador duradero fail-closed, límites, secreto privado, errores y
   privacidad. Pruebas con proveedor simulado y reinicio/concurrencia reales.
   Ninguna ampliación implícita del contrato de #2098.
3. Cliente Windows en PR separada: selector explícito, aviso de envío externo,
   credencial remota protegida por Windows, etiqueta de fuente, errores legibles
   y accesibilidad. Probar que «Tu índice» funciona con el gateway apagado y no
   genera salida Web; ni escritura ni cambios de pestaña envían consultas.
4. Activación acotada tras revisión de condiciones, cuenta, clave y coste:
   primero Python programming y Mozilla Firefox, exigiendo en cada caso tema y
   destino oficial en el mismo resultado. No relajar la prueba para lograr verde.
   Usar verificador transitorio; conservar solo resultados booleanos propios,
   versiones y contadores, sin respuesta Brave ni URLs devueltas.
   Si falla, detener y diagnosticar. Completar hasta 100 intentos solo bajo el
   cupo aprobado y sin reintentos automáticos.

Nada de lo anterior prueba por sí solo calidad general, protección familiar,
Linux/Android nativos o rentabilidad comercial. Cada entrega requiere revisión,
commits verificados y comprobaciones aplicables antes de integración.

## Parada, reversión y handoff

Antes de activación, comprobar interruptor de cierre en servidor, revocación de
credencial remota y de clave Brave. Detener gateway bloquea Web y conserva
«Tu índice». Revertir el cliente recupera la interfaz anterior sin migraciones
destructivas. No se tocan perfiles personales para probar.

Este documento y su PR son el handoff técnico de diseño. AI_HANDOFF.md no cambia
porque su contenido protegido y los otros trabajos no forman parte del alcance;
OWNER_AUTHORITY_HANDOFF.md continúa vigente. Autoridad, protecciones, firmas y
aprobación humana final permanecen intactas.

## Referencias inspeccionadas

- [Bloqueo previo #2062](https://github.com/Voxterrae/HUB_Optimus/issues/2062)
- [Catálogo remoto #2098](https://github.com/Voxterrae/HUB_Optimus/pull/2098)
- [Health local #2107](https://github.com/Voxterrae/HUB_Optimus/pull/2107)
- [API Web Brave](https://api-dashboard.search.brave.com/api-reference/web/search/get)
- [Planes Brave](https://api-dashboard.search.brave.com/app/plans?tab=normal)
- [Retención, claves y facturación Brave](https://api-dashboard.search.brave.com/documentation/resources/help-feedback)
