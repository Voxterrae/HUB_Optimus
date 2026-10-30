# Decisiones de arranque Windows 0.3.2

Fecha: 30/10/2026, Europe/Madrid. Coordinación #2021; incremento sobre el diseño nativo de #2025. No se modifica `.github/`, la política del repositorio ni la aceptación histórica.

| Orden | Decisión y motivo | Coste o límite |
| --- | --- | --- |
| 1 | Corregir el corte anticipado de veinte sondeos y usar el plazo existente de cuatro segundos. | El plazo continúa siendo finito; no garantiza arrancar en cualquier equipo. |
| 2 | Incorporar diagnóstico Windows autocontenido y reutilizar el transporte TLS de producción. | Aumenta el ZIP por su runtime Windows Desktop; requiere evidencia Windows separada. |
| 3 | Servicio con token/puerto/carpeta temporal propios; GUI solo en usuario o VM desechable sin perfil previo. | La GUI retiene el perfil nuevo; debe descartarse el entorno de prueba. No usa el equipo personal. |
| 4 | Mantener la propuesta CI fuera de `.github/workflows`. | El proceso protegido exige autoría, firma y revisión del propietario antes de activarla; la propuesta no ejecuta pruebas ni concede excepciones. |
| 5 | Comprobar procedencia de ocho PE: tres apphosts, tres DLL de entrada y dos copias Core. | Impide afirmar un mismo SHA a partir de apphosts mezclados con DLL anteriores; no sustituye firma digital ni prueba de ejecución. |
| 6 | Conservar pruebas de rutas reales en Linux y representar estados incompatibles con NTFS mediante validación léxica/ZIP y una entrada de directorio inyectada en Windows. | Las subpruebas de symlink sin privilegio se omiten de forma visible; Windows real sigue pendiente. No se relaja el empaquetador. |
| 7 | Ampliar el arreglo a la carrera de creación del token descubierta al validar. | Reproducción Linux: cuatro de veinte rondas devolvieron claves distintas. Guard persistente, exclusión verificada y plazo cancelable de cinco segundos; ocho procesos y contención probados en Linux; no demuestra reproducción en Windows. |
| 8 | Mantener Web general bloqueada hasta disponer de proveedor y resultados aceptados. | El catálogo de tres ayudas no cubre Internet. No se añaden cuentas, gastos, IA, voz, IoT ni proveedores silenciosos. |

Los manifiestos anteriores permanecen intactos. La nueva entrega se extrae completa, sin actualizar parcialmente DLL antiguas. La PR y el comentario de entrega registran el SHA público y el hash del ZIP después de publicar; estos documentos no intentan incluir su propio commit.
