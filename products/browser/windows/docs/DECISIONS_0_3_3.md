# Decisiones de apariencia Windows 0.3.3

Fecha: 31/10/2026, UTC. Coordinación #2021; incremento sobre la base pública `f8bbc2faffbd6141de7706e669753c5421f6ae23` y el draft #2026. No activa CI ni modifica protecciones, identidad o infraestructura.

| Orden | Decisión y motivo | Coste o límite |
| --- | --- | --- |
| 1 | Conservar WPF y sus recursos semánticos, con una política Core común para tema, contraste y escala. | La coherencia del código y la compilación no prueban la representación nativa en Windows. |
| 2 | Mantener Oscuro como valor inicial; Claro y Sistema son elecciones explícitas. | Evita cambiar de golpe preferencias antiguas sin campo de tema; Sistema requiere selección. |
| 3 | Dar prioridad al alto contraste de Windows, después al manual y después al tema. Consultar la preferencia del sistema solo en lectura, con fallback oscuro. | La consulta del registro y los cambios de preferencia requieren observación Windows; no se altera la política del equipo. |
| 4 | Modo fácil aplica un mínimo efectivo de 125 % y conserva el tamaño y contraste manuales. | Al apagarlo se restaura el tamaño manual; no se adapta el contenido de terceros ni se afirma accesibilidad certificada. |
| 5 | Reutilizar Ajustes desde Elegir tema y plegar proveedor/restauración bajo Otras opciones solo al iniciar o cambiar Modo fácil. | El botón, la selección nativa, el retorno de foco y el área interactiva siguen pendientes de aceptación Windows. |
| 6 | Compartir el estado efectivo con WebView2, diseño adaptable, guía local y ventanas secundarias sin recrear pestañas. | La prueba de lógica no demuestra ausencia de problemas visuales o de foco en una sesión real. |
| 7 | Conservar el servicio, TLS, diagnóstico y fuentes de búsqueda del incremento anterior. | Web general sigue sin aceptación upstream; no se añaden proveedores, voz, IA, IoT, cuentas ni gasto. |
| 8 | Cambiar solo la línea de versión de la propuesta WindowsSmoke fuera de `.github/workflows`. | La propuesta continúa inactiva; no se atribuye una ejecución Windows a CI ni a la compilación Linux. |
| 9 | Versionar la entrega como 0.3.3 y mantener guías y manifiestos históricos. | El inventario nuevo excluye su propio archivo y describe bytes de fuentes; el SHA público y la integridad del ZIP se registran aparte después de su publicación. |

La preparación de este lote no instala ni ejecuta la aplicación Windows. La publicación y el empaquetado de binarios reales se realizan desde el SHA público final, con sus verificaciones y límites separados. Reversión: carpeta completa de la versión anterior, sin mezclar DLL ni reescribir inventarios anteriores.
