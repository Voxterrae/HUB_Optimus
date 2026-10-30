# Decisiones de diseño Windows 0.3.1

| Orden | Decisión y motivo | Coste si cambia |
| --- | --- | --- |
| 1 | Adaptar la identidad ya solicitada al WPF real; conservar WebView2 y controles nativos, con carbón, acento cálido y marca menta. | Rehacer presentación nativa; no cambia infraestructura. |
| 2 | Separar shell/recursos e inicio/búsqueda con claves de recursos comunes e integrar las tareas aisladas. | Rehacer recursos o integración si divergen. |
| 3 | Verificar estilos con compilación, referencia visual y suites existentes; evitar tests que solo copien el XAML. | La aceptación Windows puede encontrar defectos visuales no cubiertos por las suites. |
| 4 | En ancho estrecho, sustituir temporalmente la región del navegador por ayuda/ajustes para respetar el HWND de WebView2. | Revisar disposición y foco si la experiencia requiere otra solución nativa. |
| 5 | Mantener como pendientes las pruebas de foco, paleta y tecnologías de apoyo que requieren Windows; corregir los fallos revisados y dar pasos reproducibles, sin fingir una ejecución. | Rehacer interacción si la aceptación en equipo detecta problemas restantes. |

La referencia MagicPath/HTML ayuda a ver el diseño. El XAML, el inicio y los estilos también están en las fuentes y el ejecutable de esta entrega. Las decisiones no constituyen aceptación humana, certificación accesible o autorización de merge.
