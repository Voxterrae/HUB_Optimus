# Apariencia nativa Windows 0.3.3

Encargo: implementar y probar pequeños lotes después de aprobar las propuestas UX. Este lote contiene Claro/Oscuro/Sistema, alto contraste independiente y Modo fácil optativo. Base pública f8bbc2faffbd6141de7706e669753c5421f6ae23, draft #2026; coordinación #2021. Usuario delegó implementación y pruebas, preferencia cloud y presupuesto cero.

## Alternativas y decisión del implementador
Cambiar todo el framework o añadir Fluent/WinRT es innecesario para este lote. Una maqueta HTML no verifica el ejecutable. Elegimos conservar WPF y los nueve recursos semánticos, con una política de apariencia Core usada por todas las ventanas. La compilación y las pruebas de lógica se ejecutan en Linux cloud; la ventana real requiere Windows y se etiqueta como pendiente.

## Contrato Core
ThemePreference: Dark=0, Light=1, System=2. BrowserSettings.Theme por defecto Dark conserva el aspecto de archivos anteriores sin campo y nuevas instalaciones; EasyMode por defecto false. SettingsStore valida enum y conserva archivos inválidos sin sobrescribirlos. No altera privacidad, proveedor, marcadores o restauración de sesión.

AppearancePolicy.Resolve(BrowserSettings settings,bool systemDark,bool systemHighContrast) devuelve un estado inmutable con Palette (Dark,Light,HighContrast,SystemHighContrast), TextScale efectivo y EasyMode. Prioridad: alto contraste de Windows, alto contraste manual, tema seleccionado. System sigue systemDark. Escala efectiva=EasyMode?Math.Max(1.25,TextScale):TextScale, dentro de1..2. No reescribe TextScale o HighContrast manuales; al apagar EasyMode se recupera la preferencia manual. Entrada de tema/escala inválida falla claramente.

## Aplicación nativa
NativeTheme aplica todos los pinceles y tamaños desde el mismo estado. Consulta de solo lectura de AppsUseLightTheme, con fallback oscuro ante ausencia/error; ninguna escritura de registro o política. Reutiliza los eventos de preferencia y dispatcher existentes. Respetar DynamicResource, controles nativos y contraste del sistema. Los sitios mantienen sus colores.

Propagar paleta y escala desde propietario a marcadores, privacidad y descargas, tanto al crear como al refrescar en vivo. Eliminar la doble aplicación ApplyContrast/NativeTheme que podría restaurar la paleta incorrecta. Mantener sus controles y acciones.

Botón sol/luna accesible «Elegir tema» en barra abre Ajustes con foco en selector Tema; selector Claro/Oscuro/Sistema, checkbox Modo fácil, Contraste alto separado. Sin popup nuevo ni ciclos ambiguos. Botón persistente participa en retorno de foco, no pierde el aviso privado pendiente. Mantener escala y estado efectivos honestos: valor manual conservado y texto breve con tamaño aplicado cuando Modo fácil eleva el mínimo. Permitir ampliar más. Con alto contraste explicar su prioridad.

Modo fácil agranda texto/controles mediante escala mínima125% y pliega proveedor/restauración bajo «Otras opciones» al activarse. Esas opciones siguen accesibles. Tema, tamaño, contraste y privacidad permanecen visibles. No cambiar la fuente de búsqueda. El plegado ocurre solo al cambiar EasyMode o al inicio; un cambio de tema/sistema no vuelve a cerrar lo que la persona abrió. Desactivar EasyMode muestra las opciones otra vez.

Todos los usos efectivos (FontSize, recursos, WebView2 ZoomFactor al crear y actualizar, cálculo de ancho adaptable, guía local y ventanas secundarias) utilizan la misma resolución. Cambiar apariencia no recrea pestañas, borra consulta o navega. Mantener 44DIP, teclado, ancho420DIP y zoom200%; aceptación real Windows pendiente.

## Entrega y pruebas
Regresiones Core con disco real: roundtrip, archivos antiguos, enum desconocido preservado; matriz tema/sistema/contraste; EasyMode on/off y escala manual preservada; límites, privacidad/marcadores/sesión intactos. No tests que solo copien XAML. Revisar contraste de valores de paleta; no atribuir certificación a esos cálculos.

0.3.3 autocontenida con diagnóstico existente y guía nueva. Mantener manifiestos0.3.2 y anteriores. PR apilada y ZIP privado tras review/build/integridad; no merge. Tres tareas de observación: tema en ventana/dialog, Modo fácil y retorno a tamaño anterior, búsqueda local y pestaña privada sin cambios. Publicar resultados y límites en #2021.

## Límites
Sin backend/voz/LLM/telemetría, nuevo proveedor, pagos, cambios de CI/protecciones/identidad/accesos ni router. Archer consta como router/almacenamiento; no es ejecutor Windows. No hay endpoint Tailscale verificado en esta sesión ni Windows cloud activado. No usar Wine/HTML/Linux build como ejecución WPF. No usar Desktop Commander por la preferencia del usuario.
