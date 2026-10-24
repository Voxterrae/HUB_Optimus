# Protocolo de Revisión por IA Externa

Este protocolo define las reglas y el formato para utilizar modelos de IA externos (por ejemplo, Claude, Gemini, Perplexity, Grok y herramientas similares) en la revisión de contenido, arquitectura y documentación dentro del repositorio HUB_Optimus.

Los modelos de IA externos son herramientas valiosas para el análisis, la revisión de código y la retroalimentación. Sin embargo, sus resultados deben mantenerse estrictamente como consultivos. Los resultados de la IA nunca deben eludir la gobernanza de Issues y Pull Requests (PR) de GitHub.

Este protocolo se alinea explícitamente con la matriz de acceso de IA definida en [Voxterrae/HUB_Optimus#1584](https://github.com/Voxterrae/HUB_Optimus/issues/1584).

## Principios

1. **Solo Consultivo:** Los modelos de IA externos siguen siendo estrictamente consultivos y nunca se convierten en la fuente de verdad.
2. **GitHub como Fuente de Verdad:** Ningún hallazgo externo puede convertirse en trabajo de implementación a menos que esté representado por un Issue o PR de GitHub. La acción directa basada en resultados de IA externa sin seguimiento de gobernanza está estrictamente prohibida.
3. **Sin Integración:** Este protocolo rige el intercambio de texto manual. La integración automatizada con proveedores de IA externos está fuera de alcance.
4. **Seguridad de Datos:** Nunca suba secretos privados, credenciales o datos de repositorios no públicos a herramientas externas.

## Reglas de Manejo de Resultados

Todos los hallazgos generados por modelos de IA externos deben ser clasificados de vuelta a GitHub:

- **Hallazgos y Sugerencias:** Si una revisión de IA externa genera hallazgos útiles, un contribuyente humano o un agente interno autorizado debe copiar las sugerencias relevantes en un Issue de GitHub o en un comentario de PR.
- **Desacuerdos:** Si el modelo de IA resalta un desacuerdo o conflicto, debe ser evaluado por un humano o un agente autorizado. Si se considera válido, debe resolverse mediante procesos estándar de consenso dentro de un PR o Issue de GitHub.
- **Trabajo de Seguimiento:** Si la IA sugiere trabajo adicional, se debe crear un Issue explícito de GitHub para su seguimiento.
- **Acción Directa Prohibida:** El resultado de una IA externa no puede canalizarse directamente a contratos de tiempo de ejecución, hoja de ruta o gobernanza sin un formato manual y seguimiento centrado en GitHub.

## Formato del Paquete de Revisión

Para garantizar que los modelos externos reciban los límites y el contexto adecuados, todas las solicitudes de revisión deben utilizar el formato estandarizado del Paquete de Revisión a continuación. Este paquete puede compartirse externamente sin otorgar autoridad.

### Plantilla Estándar del Paquete de Revisión

```markdown
### 1. Contexto
[Proporcione el objetivo de alto nivel de la revisión. Por ejemplo: "Revisar este pull request para consistencia de la documentación y alineación con los principios de gobernanza de HUB_Optimus."]

### 2. Archivos y Alcance
[Enumere los archivos específicos, fragmentos de código o secciones de documentación bajo revisión.]
- Archivo 1: `ruta/al/archivo.md`
- Archivo 2: `ruta/al/codigo.py`

### 3. Preguntas
[Especifique en qué debe enfocarse la IA. Sea explícito para evitar alucinaciones o la desviación del alcance.]
- ¿La documentación se alinea explícitamente con los principios del Kernel de Capa 0?
- ¿Existen inconsistencias lógicas en el escenario propuesto?
- ¿El código cumple con los controles de seguridad requeridos?

### 4. Restricciones
[Proporcione límites para el modelo de IA.]
- Usted actúa solo en un rol consultivo. No tiene autoridad para aprobar o fusionar estos cambios.
- No proponga reescrituras arquitectónicas radicales.
- Concéntrese estrictamente en los archivos proporcionados en el alcance.
- Mantenga la perspectiva de integridad primero.

### 5. Resultado Esperado
[Defina el formato que espera que la IA devuelva.]
- Una lista con viñetas de hallazgos específicos.
- Para cada hallazgo, proporcione el nombre del archivo y el cambio sugerido.
- Una breve justificación basada en evaluación sistémica, no en preferencia personal.
```
