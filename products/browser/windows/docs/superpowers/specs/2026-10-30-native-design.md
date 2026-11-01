# Optimus Windows — llevar el diseño aprobado a la aplicación

El usuario solicita corregir la diferencia entre el diseño futurista y sencillo ya encargado/aprobado y la interfaz Windows técnica mostrada. Implementar en WPF, preservando WebView2 y el buscador 0.3. No repetir aprobación de estilo: dirección visual y ejecución delegadas en este hilo. Referencia MagicPath verificada componente466697341487947776/revisión466698922518265856.

## Dirección y alternativas
Adaptar la identidad existente a WPF nativo: elegida por continuidad del runtime y controles accesibles. Incrustar toda la interfaz React dentro de un WebView añadiría un puente y sustituiría controles nativos; no encaja en este incremento. Crear otra maqueta sin modificar el ejecutable dejaría sin resolver la petición.

## Apariencia e interacción
Fondo carbón #0F1217, superficies #171C24/#202731, texto #F5F2EC, secundario #B7BEC9, acento cálido #EDB77D y marca menta existente #54E0C1. Logo original; sin imágenes decorativas, parpadeos o glow que reduzca legibilidad. Tipografía Segoe UI; cuerpo18DIP, controles44DIP mínimo y foco visible. Mantener barra de título de Windows.

Navegación superior compacta: marca, pestañas en una sola fila desplazable, Atrás/Adelante/Recargar/Inicio, dirección/búsqueda expansible y menú. Barra lateral en ancho suficiente con Inicio, Guardados, Ayuda y Ajustes. Controles poco frecuentes dentro de menú/panel de ajustes cerrado por defecto. Sin panel de ayuda inicial. Nunca ocultar aviso de destino privado pendiente ni errores.

Inicio nativo con titular «Menos ruido. Más tú.», buscador grande real, fuente Web/Índice/Wikipedia explícita y tarjetas de entrada sencillas. Índice explica su corpus finito, Web mantiene su configuración/bloqueo. Sin voz o IA falsa, botones decorativos ni resultados inventados. Búsquedas siguen el gate de elegibilidad y cancelación existente. Ayuda real bajo demanda.

Diseño adaptable: a ancho efectivo inferior980DIP colapsar lateral; inferior680DIP compactar marcas/textos opcionales y sustituir la región del navegador por el panel, respetando el HWND/airspace de WebView2. Ancho efectivo=ancho disponible/escalaTexto. A 420DIP y escala200% permitir scrollvertical donde corresponda y controles alcanzables; no barra horizontal global. Las pestañas tienen scrollhorizontal local, no se envuelven en varias filas. Ayuda/ajustes cerrables con teclado/Escape, foco vuelve al disparador. No esconder/descartar propuestas al cambiar tamaño; navegación y cancelación conservan su política.

Recursos compartidos: OptimusPageBrush, OptimusPanelBrush, OptimusRaisedBrush, OptimusBorderBrush, OptimusTextBrush, OptimusMutedBrush, OptimusWarmBrush, OptimusAccentBrush; tamaños OptimusBodySize, OptimusSmallSize, OptimusTitleSize. Usar DynamicResource/SetResourceReference para controles nativos. Contraste alto de ajustes o del sistema prevalece sobre la paleta y se actualiza en ventanas/dialogos.

## Alcance y evidencia
MainWindow.xaml + partialChrome, App.xaml + tema y helper de apariencia, inicio y presentación de Search. No tocar Core de red/privacidad, backend, proveedores, Linux/demo/root/CI. Versión de distribución 0.3.1-alpha separada. Nueva PR apilada sobre#2022, coordinación#2021; no merge. Actualizar manifiesto propio sin sobrescribir el histórico0.3.

Validar compilación WPF, suites existentes y empaquetado real. Mostrar vista visual HTML fiel como referencia, claramente distinta de una captura de WPF. No hay Windows físico en el entorno: aceptación con Narrador/NVDA/WebView2 queda pendiente. ZIP y fuentes deben incluir el nuevo XAML/tema, no solo la vista previa.
