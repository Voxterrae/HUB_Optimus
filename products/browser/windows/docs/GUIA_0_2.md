# Optimus Browser 0.2 — guía de la alpha privada

## Abrir

Descomprime el ZIP completo en una carpeta nueva. Conserva la versión anterior por si necesitas volver. Abre **Optimus.exe** junto a sus DLL. Incluye .NET; Windows necesita WebView2 Evergreen. No modifica el navegador predeterminado.

La entrega no tiene firma digital. SmartScreen puede mostrar «Windows protegió su PC». Si verificaste el origen de este ZIP y decides probar la alpha, **Más información** muestra el ejecutable y permite **Ejecutar de todas formas** cuando la política del equipo lo admite. Mantén Defender y SmartScreen activados. Esta advertencia no confirma por sí sola seguridad ni malware.

## Identidad y búsqueda

El nuevo icono y la marca Optimus aparecen en el ejecutable, ventana y portada. La búsqueda integrada **Optimus** ofrece resultados reales de **Wikipedia en español y marcadores**; no es un índice de toda Internet ni una respuesta generada por IA. La consulta se envía a Wikipedia al pulsar Buscar/Ir; ese proveedor recibe la consulta y puede ver la dirección de conexión. No se hacen consultas remotas al escribir.

Si se conserva un perfil 0.1 con Google o DuckDuckGo elegido, se respeta esa preferencia: selecciona Optimus para usar la nueva vista. La primera apertura toma las preferencias anteriores; los ajustes de 0.2 se guardan por separado para conservar la configuración de 0.1. Google/DuckDuckGo siguen siendo elecciones externas explícitas. No hay cambio oculto de proveedor si una fuente falla.

Para búsqueda web amplia, el operador puede configurar una instancia propia/controlada de SearXNG en las opciones de privacidad/búsqueda. Debe admitir JSON. El programa no instala un servidor, no contrata servicios y no elige una instancia pública por ti. SearXNG consulta motores externos; su operación y disponibilidad dependen del servidor y sus proveedores. Dejar el campo vacío mantiene Wikipedia y marcadores.

Consultas y resultados son temporales. La búsqueda privada excluye los marcadores normales. Cancelar, cambiar de contexto o cerrar la pestaña descarta la búsqueda pendiente; una respuesta tardía no debe reaparecer. Los resultados se muestran como texto y enlaces, nunca como código del proveedor.

## Privado

Usa **Nueva privada** para iniciar una sesión separada del perfil normal. Comprueba el indicador **Privado**. Las pestañas privadas de esta ejecución comparten sesión entre sí y permanecen privadas hasta cerrarse; no se convierten en normales al cambiar de web.

Las reglas locales permiten abrir ciertos dominios automáticamente en privado o bloquearlos. Incluyen una lista inicial pequeña y editable de dominios adultos comunes, sin cobertura completa. Puedes añadir tus propios dominios; una regla incluye ese dominio y sus subdominios reales. No se decide la ética de una web ni se envía su contenido a un clasificador.

Una dirección escrita, un marcador o un resultado abierto desde los controles de Optimus se evalúa antes de navegar. Si coincide con una regla Privado, se abre en la sesión privada. Los enlaces, redirecciones y formularios cuyo método/contexto no se pueda determinar se detienen y permiten abrir el sitio explícitamente en privado. No se reenvían formularios automáticamente. Los recursos secundarios y workers afectados pueden bloquearse; algunas páginas pueden funcionar de forma incompleta.

Cambiar reglas requiere detener las páginas abiertas y descartar acciones/búsquedas pendientes. El diálogo avisa antes: conserva primero el texto que no hayas guardado. Una regla nueva no deshace contactos previos con un sitio.

Las direcciones privadas no se guardan en restauración, lista de pestañas cerradas ni ajustes. Los marcadores y archivos que decidas guardar sí pueden permanecer: revisa sus avisos. El modo privado limita la persistencia local; **no proporciona anonimato, VPN, borrado forense ni protección adicional contra malware**. Una web, el proveedor de red o un administrador pueden observar actividad. El motor y Windows conservan sus propias funciones de seguridad; su funcionamiento efectivo depende de políticas y runtime.

## Prueba controlada en Windows

Esta 0.2 está compilada y revisada desde Linux, pendiente de aceptación en Windows. Que 0.1 haya abierto en tu equipo no verifica los cambios nuevos. Prueba inicialmente sin información sensible y con páginas/dominios de prueba propios.

- Comprueba icono en ventana/barra de tareas, teclado Ctrl+L y F1, zoom200%, contraste y ventana estrecha.
- Usa una regla Privado sobre un dominio de prueba. Verifica indicador y cookies separadas entre normal/privado; cierra todas las privadas y comprueba una sesión nueva.
- Activa restauración: una URL privada, búsqueda o destino interceptado nunca debe reaparecer al reiniciar ni en pestañas cerradas.
- Comprueba enlaces, iframe, GET/POST, redirecciones307/308, popup de formulario y service/shared workers con un servidor que registre solicitudes/cookies. Una prueba negativa real es necesaria antes de afirmar que ningún dato salió.
- Cambia reglas durante una página/búsqueda y revoca permisos; recupera una pestaña. El modo privado debe conservarse y las respuestas/acciones anteriores quedar descartadas.
- Busca un término en Wikipedia; prueba fallo de red y JSON inválido en un backend de prueba. Deben aparecer errores reales, sin resultados fabricados ni cambio silencioso a otro motor.
- Comprueba borrado de datos para perfiles normal/privado, descargas canceladas y bloqueo de navegación tras timeout/fallo. Los archivos descargados y marcadores explícitos no se borran por esa acción.

La aceptación de estas rutas, accesibilidad y ausencia de filtraciones reales sigue pendiente. Conserva una copia del ZIP y comunica el paso concreto y el mensaje visible si falla. La guía local sigue basada en reglas; la IA generativa nativa no está conectada.
