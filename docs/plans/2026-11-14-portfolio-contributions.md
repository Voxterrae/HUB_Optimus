# Portfolio y registro de contribuciones

Related to #2185. Refs #1936; ambas incidencias permanecen abiertas.

## Resultado autorizado

Ampliar el portfolio existente con aportaciones públicas acreditadas y un índice
del histórico Git desde su raíz. Reutilizar el catálogo de 17 componentes y
presentar Project Intelligence como creación experimental vinculada a Labs.
La cobertura histórica debe poder comprobarse y conservar sus límites.

## Pasos

1. Auditar fuentes públicas y fijar raíz, corte y estados de aportaciones.
2. Añadir registro Markdown, JSON e índice de commits sin correos ni datos privados.
3. Incorporar una sección estática al portfolio y textos en sus seis idiomas;
   conservar las rutas, los componentes y los estados del catálogo actual.
4. Comprobar correspondencia entre fuentes, datos y texto visible, ejecutar las
   pruebas del sitio y revisar el diff completo antes de una PR en borrador.

## Límites y decisiones

- El índice de commits cubre el grafo alcanzable hasta un SHA, no todas las
  conversaciones, aportaciones eliminadas, ramas no integradas o trabajo privado.
- El índice de búsquedas externas tiene lagunas demostradas; los objetos leídos
  directamente prevalecen sobre el recuento de resultados de búsqueda.
- No publicar URLs ni contenido de superficies con acceso restringido.
- Un comentario de validación no es el parche upstream; una PR abierta no es
  una aportación integrada. Conservar autoría y asistencia de IA explícitas.
- Sin cambios a productos, dependencias, workflows, contratos de capacidades,
  autoridad, servicios o despliegues. Sin integración automática.

## Verificación

Pruebas existentes de portfolio, catálogo, registry, enlaces, contraste,
interacción estática y Project Intelligence, más controles de coherencia del
registro y de su cobertura. Revisar render móvil/escritorio y cambio de idioma.
La aprobación humana y los checks de la PR siguen pendientes de su ejecución.
