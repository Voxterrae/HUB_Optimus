# Optimus Windows 0.3.3 alpha — apariencia y Modo fácil

Al recibir el ZIP de esta versión, extráelo completo en una carpeta nueva y abre `Optimus.exe`, conservando `Search/` y `Diagnostics/` junto a él. El título debe mostrar **0.3.3 alpha**. Requiere Windows x64 y WebView2 Evergreen; los runtimes .NET se incluyen en la publicación autocontenida. Es una alpha privada sin firma. La compilación Linux no acredita su ejecución ni su accesibilidad en Windows.

## Elegir la apariencia

Pulsa el botón **Elegir tema** de la barra. Abre los ajustes existentes y lleva el foco al selector **Tema**, con **Oscuro**, **Claro** y **Sistema**. Oscuro sigue siendo el valor inicial, también al cargar preferencias antiguas sin este campo. Sistema sigue la preferencia de aplicaciones de Windows; si no puede consultarla, usa oscuro. La aplicación solo lee esa preferencia.

Los colores y el tamaño se comparten con marcadores, privacidad y descargas. Cambiar el tema no debería recrear pestañas, borrar una consulta ni navegar. Los sitios conservan sus propios colores. **Contraste alto** continúa siendo un ajuste independiente; el alto contraste de Windows tiene prioridad sobre los colores seleccionados y después se aplica el contraste manual.

## Usar Modo fácil

Activa **Modo fácil** en ajustes para aplicar un tamaño mínimo del **125 %**. Puedes elegir un tamaño mayor, hasta el 200 %. El valor manual se conserva: si era 100 %, al apagar Modo fácil vuelve a aplicarse 100 %; si era 150 %, permanece en 150 %. El texto de los ajustes distingue la preferencia guardada del tamaño efectivo.

Al activar Modo fácil se pliega **Otras opciones**, que contiene proveedor y restauración de sesión. Puedes abrirla cuando la necesites. Cambiar el tema o la preferencia del sistema no debe volver a cerrar una sección que has abierto. Al desactivar Modo fácil, las opciones vuelven a mostrarse. Tema, tamaño, contraste y privacidad siguen accesibles. Modo fácil no cambia la fuente de búsqueda ni las reglas de privacidad.

## Tres observaciones en Windows

Estas son tareas de aceptación pendientes, no resultados ya obtenidos:

1. Cambia entre Claro, Oscuro y Sistema; abre marcadores, privacidad y descargas y comprueba colores, texto seleccionado y foco. Prueba también un cambio de preferencia y de alto contraste de Windows con una ventana secundaria abierta.
2. Guarda 100 %, activa Modo fácil y observa el mínimo 125 %. Abre Otras opciones, cambia el tema y comprueba que sigue abierta. Desactiva Modo fácil y comprueba que vuelve el 100 %. Repite con 150 % y revisa teclado, ancho 420 DIP y zoom 200 %.
3. En Inicio, elige **Tu índice** y busca **servicio local**. El catálogo de tres ayudas debería devolver «Ayuda Optimus: servicio local y privacidad». Abre una pestaña privada y cambia la apariencia: la fuente de búsqueda, la consulta y el aviso privado pendiente deben conservarse.

La aceptación completa requiere además teclado real, Narrador/NVDA, foco, áreas de interacción de 44 DIP, contraste y comportamiento WebView2. Las capturas o la compilación no sustituyen esas observaciones.

## Diagnóstico del servicio

El diagnóstico existente se conserva. En Windows PowerShell, desde la carpeta recibida:

```powershell
powershell.exe -NoProfile -File .\Test-OptimusWindows.ps1 -Publication $PWD.Path
```

Comprueba el SearchHost publicado con puerto y carpeta temporal propios: identidad TLS, autorización y resultado del catálogo. No usa el perfil ni el token habituales. Añade `-SourceCommit` con el SHA completo registrado en la PR de entrega para exigirlo en ProductVersion de los tres apphosts, sus DLL de entrada y las dos copias de Core. Sin ese argumento, la procedencia figura como `not-requested`; un hash no equivale a firma digital.

La opción `-Gui` es exclusiva de una VM o usuario desechable, con escritorio interactivo, WebView2 y sin perfil Optimus previo. Conserva el perfil recién creado para diagnóstico; después hay que descartar ese entorno. La ausencia de requisitos produce bloqueo, nunca aceptación. Consulta la [guía del diagnóstico 0.3.2](GUIA_0_3_2.md) para códigos de salida y límites. No desactives políticas del equipo si SmartScreen o la política de scripts bloquean la alpha.

## Límites y vuelta atrás

Web general continúa necesitando un SearXNG del operador y aceptación de resultados. El índice local finito y Wikipedia explícita no sustituyen un buscador mundial. No se conectan voz, IA generativa ni IoT. El modo privado limita persistencia local; no ofrece anonimato.

La [validación 0.3.3](VALIDATION_0_3_3.md) distingue las pruebas realizadas de las pendientes. La PR y el comentario de entrega registrarán el SHA público y los hashes del ZIP después de preparar y verificar la publicación. No copies perfiles, tokens ni informes personales a la entrega. Para volver atrás, abre la carpeta completa de la alpha anterior; no mezcles DLL ni modifiques sus manifiestos históricos.
