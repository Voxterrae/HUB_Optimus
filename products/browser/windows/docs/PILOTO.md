> **Actualización 0.2:** consulta [GUIA_0_2.md](GUIA_0_2.md) para identidad, búsqueda nativa y privado/reglas. El usuario reportó que 0.1 abre en Windows;0.2 y sus rutas de privacidad todavía requieren aceptación real. Las secciones históricas de 0.1 siguientes no describen las nuevas opciones de búsqueda y perfiles.

# Operación del piloto privado Optimus Browser 0.1.0

## Estado y requisitos

Esta entrega valida un núcleo local y una aplicación WPF/WebView2 compilada para Windows x64. **No está firmada, no es una publicación pública y requiere ejecución de aceptación en Windows antes de usarla con información real.** La IA remota no está conectada; su autenticación y autorización individuales siguen pendientes de validar. El presupuesto autorizado es cero. No hay llamadas pagadas, claves de proveedor ni token compartido de Sites en el cliente. No se incluye un instalador.

Base de validación: Windows 11 x64. Requiere .NET **Desktop** Runtime 10 x64 (no solo ASP.NET o .NET Runtime) y Microsoft Edge WebView2 Evergreen Runtime. El SDK de compilación está fijado a 10.0.403; el entorno de construcción utilizado tiene runtime 10.0.14. WebView2 SDK fijado a **1.0.4314.35**, seleccionado del índice real de NuGet el 29-10-2026 como última versión sin sufijo de prerelease. El runtime Evergreen se actualiza por su propio mecanismo. El SDK no incluye ni instala ese runtime.

Fuentes oficiales para el operador:

- [.NET 10](https://dotnet.microsoft.com/download/dotnet/10.0): elegir .NET Desktop Runtime, Windows x64.
- [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/): comprobar la instalación Evergreen de Windows antes de instalar nada.
- [Privacidad y SmartScreen de WebView2](https://learn.microsoft.com/microsoft-edge/webview2/concepts/data-privacy).
- [Seguridad de WebView2](https://learn.microsoft.com/microsoft-edge/webview2/concepts/security).
- [Metadatos del SDK fijado](https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/index.json).

No se descargan o instalan herramientas automáticamente. La instalación de los requisitos es una decisión del operador. No se modifica el navegador predeterminado, políticas del equipo ni otros perfiles. No desactives avisos de certificados o SmartScreen para aprobar una prueba. La ausencia de firma debe tratarse como estado de distribución privada pendiente de revisión.

## Abrir y usar

1. Extrae y conserva junta toda la carpeta publicada para win-x64. Comprueba `SHA256SUMS.txt` desde una copia confiable mediante `Verify-Optimus.ps1` o `Get-FileHash`.
2. En Windows con los requisitos instalados, abre `Optimus.exe`. No necesita permisos de administrador.
3. Escribe una dirección HTTP/HTTPS o palabras en Dirección o búsqueda. El buscador se elige explícitamente entre DuckDuckGo y Google. El navegador envía la búsqueda a ese sitio como navegación ordinaria.
4. Usa Nueva pestaña, Cerrar pestaña, Recuperar pestaña y Marcadores. Guardar un marcador también está disponible dentro de Marcadores. Las pestañas cerradas solo se recuperan durante la sesión actual.
5. Abre Ayuda. El botón Consultar guía local utiliza reglas locales, no un modelo ni un proveedor simulado. Prueba «abre https://example.org», «guardar marcador», «aumentar zoom» o «permiso cámara». La propuesta muestra el cambio concreto; Confirmar acción solo funciona una vez y dentro de 60 segundos. Cancelar, Escape, cerrar Ayuda, cambiar de pestaña o comenzar otra navegación la revocan.
6. Selecciona texto del documento principal y pulsa Revisar selección. No se capturan formularios, campos editables ni documentos de iframes. La selección se descarta si cambia el documento mientras se obtiene. La vista previa admite edición o texto pegado; Revisar texto pegado comprueba el origen de la página actual. Los textos de más de 8.000 caracteres se recortan solo al revisar, con un aviso. El envío permanece desactivado: destinatario ninguno. Navegar no consulta ningún servicio de IA.

Atajos: Ctrl+L lleva a la dirección; Intro navega; Ctrl+N abre pestaña; F1 abre ayuda; Escape cancela propuesta y vista previa. Los botones mantienen sus posiciones. El tamaño de los controles y el zoom van de 100 a 200 %; el contraste alto afecta a los controles nativos, y las páginas conservan sus propios colores. No se infiere ninguna capacidad del usuario.

Las páginas iniciales son **candidatos sin verificar**. El registro de atribución oficial existe como núcleo, pero se entrega vacío: un operador debe comprobar referencias institucionales, anotar dominio exacto, referencia y fecha antes de añadir entradas. Un subdominio requiere su propia entrada. Pasados 30 días la revisión se marca pendiente; ni HTTPS ni el texto de la guía confirman oficialidad.

## Permisos, descargas y datos

Se deniegan por defecto los permisos. Solo solicitudes iniciadas por el usuario en la pestaña visible pueden mostrar un aviso nativo con el origen y el recurso. Cámara, micrófono, ubicación y notificaciones requieren una decisión específica; el resto de permisos y la captura de pantalla se deniegan en este piloto. Las decisiones no se guardan en el perfil (`SavesInProfile=false`). Revocar permisos cierra y reabre todos los documentos tras un aviso: puede perderse texto no guardado y se interrumpe el uso de recursos. Las ventanas emergentes sin interacción se bloquean. Los protocolos externos se bloquean; el piloto solo navega a HTTP/HTTPS. Un sitio que requiera protocolos externos debe probarse por separado en un navegador del sistema abierto por la persona.

Las descargas requieren un destino elegido en el diálogo Guardar, muestran ruta, bytes y estado en Descargas, y permiten cancelar. Ningún archivo se abre o ejecuta automáticamente. El cierre cancela las descargas en curso; el listado de Optimus no se conserva entre sesiones. Un archivo ya guardado no se elimina al borrar datos del navegador.

Los archivos propios están en `%LOCALAPPDATA%\Optimus\private-pilot`:

- `settings.json`: marcadores, buscador, tamaño, contraste y opción de restauración. **Solo al activar Restaurar direcciones al abrir se guardan las direcciones de las pestañas.** Desactivarla elimina esa lista de los ajustes. No se guarda un historial general de navegación de la aplicación.
- `WebView2`: perfil del motor con cookies y datos de sitios. Contraseñas y autocompletar están desactivados tanto en el control como en el perfil. El historial del motor se borra al iniciar, antes de habilitar navegación, y al cerrar. Un cierre forzado puede impedir el borrado final; se reintenta al abrir. No se promete borrado forense de journals del motor o copias del sistema.

«Borrar datos de sitios» es una acción explícita con confirmación del alcance: **todos los datos del perfil del motor** (`CoreWebView2BrowsingDataKinds.AllProfile`), incluidos cookies, caché, almacenamiento de sitios, service workers, permisos, historial, registro de descargas y autocompletar. Cierra las páginas y cancela descargas. Conserva los marcadores y ajustes de Optimus, y no elimina los archivos descargados del disco. El motor puede ampliar los tipos incluidos en AllProfile; las credenciales de cuentas de terceros no se borran de sus servidores. No hay borrado por sitio en esta entrega.

No se registran URLs, preguntas o selecciones en archivos de diagnóstico de la aplicación. La comprobación de reputación se solicita al motor, sin afirmar que la política efectiva de Windows permita SmartScreen. WebView2 y las webs pueden efectuar conexiones propias a Microsoft y a terceros; ausencia de analítica propia no equivale a ausencia de esas conexiones.

## Recuperación

- **Falta runtime o perfil inaccesible:** la barra de estado indica cómo revisar requisitos, espacio y permisos. La guía local permanece disponible. Tras corregir el problema, usa Nueva pestaña o reinicia. No borres el perfil sin revisar qué datos conserva.
- **Fallo del proceso web:** el contenido de esa pestaña se sustituye por un aviso nativo y Recuperar esta pestaña. Recuperar vuelve a la última dirección conocida; el texto no guardado puede perderse. No se confirma éxito si el motor no responde.
- **Error de navegación o certificado:** recargar, volver o Inicio son salidas. Los errores de certificado permanecen bloqueados; no existe un botón para ignorarlos.
- **Ajustes dañados:** el original se conserva y el guardado se bloquea para evitar sobrescribirlo. Cierra Optimus, copia `settings.json` a un lugar seguro y renómbralo, por ejemplo a `settings.corrupt.json`. Abre de nuevo para empezar con valores iniciales. La copia puede contener marcadores y direcciones opt-in; trátala como información local privada. No se borra automáticamente.
- **No se borraron datos al cerrar:** se muestra un aviso; vuelve a abrir para reintentar. Si el motor falla de forma persistente, conserva el perfil y pide revisión antes de afirmar que se eliminó el historial.

## Aceptación manual pendiente en Windows

Anota Windows y versión, runtime .NET Desktop, WebView2 Runtime, hardware, fecha y resultado. Todas las casillas están pendientes hasta observar su ejecución; la compilación cruzada no las aprueba.

- [ ] Inicio sin .NET Desktop y sin WebView2: mensaje recuperable, sin instalación silenciosa ni cierre que afirme éxito. Probar perfil sin permiso de escritura y disco sin espacio.
- [ ] Direcciones, ambos buscadores, Atrás/Adelante/Recargar/Inicio, pestañas/cierre/recuperación, marcadores en otra sesión y restauración solo opt-in. Direcciones con credenciales, control, esquemas ejecutables/locales y redirecciones se rechazan.
- [ ] Recorrido completo por teclado y Narrador: foco visible, nombres comprensibles, dirección y marco siempre visibles. Probar a 200 % de tamaño de texto/zoom y escalado de Windows; las barras superiores se pueden recorrer horizontalmente. Probar contraste de Windows y de Optimus. Ajustar cualquier control que no siga siendo utilizable.
- [ ] Matriz de compatibilidad: búsqueda, ayuntamiento, correo web, PDF, descarga e inicio de sesión. Registrar dominios/versiones y salida para cada incompatibilidad. Windows 10 debe tener su propia evidencia; no hereda la aprobación de Windows 11.
- [ ] Propuesta confirmada dos veces; a 59/60 segundos; pestaña/documento/origen cambiados; nueva navegación que redirige; Cancelar/Escape; cerrar/abrir Ayuda; ninguna acción sobreviviente. Pruebas con reloj retrasado y suspensión del sistema.
- [ ] Selección de párrafo, iframe, input, textarea, contenteditable, selección que atraviesa campos, página que cambia durante extracción, más de 8.000 caracteres y emoji en el borde; aviso exacto de recorte, origen sin ruta/query/hash y revocación de la vista previa. Editar/pegar no transmite contenido.
- [ ] Permisos solicitados por la pestaña visible, por iframe y por página de fondo; denegar por defecto, etiqueta del origen real, sin concesión por guía. Revocar detiene cámara/micrófono/ubicación y reabre documentos con aviso.
- [ ] Descargar a destino visible, cancelar Guardar, cancelar en curso, error de disco/red y cerrar con descarga activa. Ningún ejecutable se abre automáticamente; borrar datos no borra el archivo descargado.
- [ ] Página maliciosa intenta `chrome.webview.hostObjects`, postMessage, ventanas automáticas, esquemas externos y certificados inválidos: sin objetos nativos, sin respuesta privilegiada, sin claves, sin bypass. Texto de página/guía siempre como texto nativo, sin interpretación de HTML o código.
- [ ] Detener proceso renderer/browser WebView2: aviso y recuperación nativa; ninguna propuesta o vista previa vieja. Cerrar durante inicio, selección y descarga no deja ejecución pendiente ni cierre bloqueado.
- [ ] Captura de red con datos sintéticos: navegar, preguntar a guía y revisar fragmento no llaman al servicio IA; solo conexiones del motor/webs. Revisar archivos propios sin contenido de preguntas/selecciones y sin lista de URLs con restauración desactivada.
- [ ] Borrar todos los datos: aviso exacto, cookies/sesiones eliminadas, páginas en Inicio; marcadores/ajustes conservados. Cierre forzado y reinicio: borrado del historial antes de habilitar navegación. Archivo de ajustes dañado conservado, sin sobrescritura y con recuperación comprobada.

Las pruebas de cinco participantes, comparación de tiempos, comprensión, rendimiento y conversación/plugin reales del diseño quedan fuera de esta compilación y pendientes. No ampliar distribución antes de resolver fallos de aislamiento, exposición o ejecución sin confirmación.

## Escenarios adicionales tras revisión nativa · ronda 1

Los siguientes escenarios siguen pendientes de ejecución real en Windows; las pruebas Linux solo ejecutan las políticas independientes, no callbacks WPF/WebView2 ni diálogos nativos.

- [ ] Con depuración nativa de WebView2, solicitar cámara/micrófono y descargar un archivo: comprobar que MessageBox/Guardar se abren en un turno de Dispatcher posterior al retorno de PermissionRequested/DownloadStarting. Cancelar, provocar excepción de diálogo, cerrar la pestaña y revocar antes de procesar el turno pendiente: cada deferral termina una vez, sin cuelgue ni concesión/descarga vieja. Cambiar documento/origen mientras el diálogo está abierto: se rechaza la respuesta obsoleta.
- [ ] Retrasar de forma controlada AllProfile más de 15 segundos: aparece el aviso de reinicio, el Task real sigue observado, no se abre una pestaña nueva ni se navega desde controles/Inicio/marcadores/propuestas. Completar o fallar tardíamente: el perfil sigue bloqueado en esa sesión, incluso después de aplicar de nuevo las preferencias seguras. Cerrar y volver a abrir Optimus es la salida controlada; no se lanza otro borrado de historial contra el perfil pendiente al cerrar.
- [ ] Durante CreateEnvironment, EnsureCoreWebView2 y limpieza inicial de historial, pulsar Cerrar pestaña, Recuperar, Revocar permisos, Nueva pestaña y cerrar la ventana: la destrucción espera su turno, se crea la pestaña de reemplazo cuando corresponde y el cierre de la aplicación cancela las continuaciones antes de tocar un control descartado. Sin NullReferenceException ni resurrección de pestañas.
- [ ] Provocar un fallo real de guardado de marcador (directorio sin permiso o almacenamiento lleno), recuperar el almacenamiento y volver a guardar exactamente la misma URL: debe reintentar la escritura, conservar un solo marcador y sobrevivir al reinicio. Un intento fallido se retira de la lista en memoria.

Si el borrado de perfil excede el límite de espera, Optimus conserva la tarea subyacente y exige cerrar/reabrir; no vuelve a habilitar navegación por la mera finalización del temporizador. La tarea puede finalizar después, pero el perfil permanece bloqueado durante esa sesión. El aviso de fallo no significa que se haya cancelado o completado el borrado.

## Restauración de direcciones del mismo documento · revisión ronda 2

- [ ] En Windows, activar Restaurar direcciones al abrir, navegar a una página y cambiar a otro fragmento `#...` sin recargar el documento. Cerrar normalmente y abrir Optimus: la dirección restaurada debe contener el fragmento final exacto. Repetir después de un segundo cambio de fragmento.
- [ ] En una SPA de prueba, usar navegación interna con `history.pushState` y `history.replaceState` que cambie ruta, query y fragmento sin NavigationStarting. Cerrar/abrir con restauración opt-in: debe restaurarse la última URL mostrada por el motor. No se debe restaurar una ruta anterior por conservar el valor de NavigationStarting.
- [ ] Después de esos cambios, provocar una lectura de Source no disponible o un fallo del motor: el valor de recuperación conserva la última URL válida. Navegar internamente a Inicio/`about:blank` y borrar datos no reemplaza ese valor de recuperación con destinos locales o vacíos; las pestañas Inicio siguen excluidas de las direcciones de sesión guardadas.

Estas comprobaciones WPF/WebView2 siguen pendientes. La regresión automática solo comprueba la política usada para actualizar/conservar la instantánea; no simula callbacks reales ni afirma que una SPA se haya ejecutado en Linux.
