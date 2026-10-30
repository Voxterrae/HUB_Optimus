# Optimus Windows 0.3.1 alpha — diseño nativo

Esta versión aplica al ejecutable Windows la línea visual de Optimus. Descomprime todo el ZIP nuevo en una carpeta propia y abre su Optimus.exe conservando Search/. El título muestra 0.3.1: una carpeta anterior no se actualiza sola. Alpha sin firma y sin aceptación en Windows físico en el entorno de compilación; mantén las protecciones de Windows.

## Empezar

El inicio muestra «Menos ruido. Más tú.» y un buscador grande. Escribe tu consulta, elige Web, Índice Optimus o Wikipedia y pulsa Buscar o Intro. El botón Tu índice abre la búsqueda local sin enviar una consulta. Para probar la ayuda incluida: Índice Optimus y «servicio local».

Web necesita un SearXNG configurado por el operador y sigue sin aceptación de resultados generales relevantes. Índice Optimus cubre únicamente los documentos importados; la entrega inicial contiene tres ayudas. Wikipedia es una elección explícita. La barra de direcciones usa el proveedor elegido en Ajustes; con Optimus Search inicia la fuente Web.

## Navegar y encontrar los controles

La barra superior contiene navegación, dirección y menú ☰. Las pestañas van en una sola fila desplazable. En ventanas anchas aparece el lateral Inicio, Guardados, Ayuda y Pestaña; al estrechar, esas acciones siguen en el menú. Los ajustes y la ayuda están cerrados al empezar.

Ajustes permite ampliar texto/zoom al 125,150 o200%, activar contraste alto, elegir proveedor y abrir los controles existentes de privacidad. El contraste alto de Windows también prevalece sobre la paleta. Al abrir ayuda en una ventana estrecha se sustituye la región de la página, para respetar WebView2; cerrar ayuda devuelve la página. Escape cierra el panel y cancela propuestas/vistas previas como antes. El aviso para abrir un destino en privado permanece accesible en la barra.

Atajos: Ctrl+L dirección, Ctrl+N pestaña, Ctrl+Mayús+N privada, Ctrl+W cerrar pestaña, F1 ayuda, F5 recargar, Alt+Inicio inicio y Alt+flechas navegación. También están disponibles desde botones/menú. Los controles tienen nombre accesible y un mínimo44DIP; su conformidad con Narrador/NVDA requiere pruebas Windows.

## Qué se conserva

El motor sigue siendo WebView2. La presentación no cambia el token, TLS, proveedores, reglas por dominio, cancelación, permisos, descargas o borrado de perfiles. El modo Privado limita persistencia local y no ofrece anonimato. La guía es local; IA remota, voz e IoT no se activan con este diseño.

La vista de MagicPath/HTML es una referencia visual de la implementación, no una captura del ejecutable. El código XAML, el inicio y las tarjetas de búsqueda sí se incluyen en el binario nuevo. Las guías 0.2 y0.3 se conservan como documentos anteriores; no acreditan esta aceptación.

## Aceptación pendiente

Probar en Windows físico: arranque, cambio de pestañas, navegación real, teclado/foco, 420DIP, texto200%, Narrador/NVDA, contraste alto propio/del sistema, paneles junto a WebView2 y modo privado. No se afirma certificación accesible, ausencia de fallos o búsqueda mundial.

## Regresiones de interacción para comprobar en Windows

1. En el buscador o selector de fuente, pulsa Escape con paneles cerrados: el foco debe quedarse en el control; las cancelaciones de propuestas/vistas previas siguen disponibles.
2. Abre Ayuda o Ajustes desde el menú y ciérralos: vuelve el foco al botón Menú. Desde un botón persistente del lateral/inicio, vuelve a ese botón si sigue visible.
3. En ancho compacto, confirma Abrir URL desde la ayuda: la ayuda se cierra y se muestra el destino. Desde Ajustes, Abrir sitio actual en privado muestra la nueva pestaña. Recuperar pestaña, atrás y recargar también muestran la región del navegador.
4. Con un destino privado pendiente, abrir/cerrar Ajustes y cambiar tamaño de ventana conserva el aviso. Navegar/cambiar política o pestaña conserva las invalidaciones de seguridad anteriores.
5. Con Descargas abierta, activa/desactiva contraste de Optimus: ambas ventanas cambian. Con un diálogo modal abierto, cambia el contraste de Windows y después su paleta sin desactivarlo: todas las ventanas nativas deben actualizarse.

Estos pasos son aceptación pendiente en equipo Windows, no pruebas ejecutadas en Linux.
