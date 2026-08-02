# Guía de uso de Operator

> **Estado:** prototipo público con revisión humana obligatoria.
> **Última revisión:** 2026-08-02.
> **Base auditada:** [`c399c94`](https://github.com/Voxterrae/HUB_Optimus/commit/c399c94e098058a723482001811c7d8491ebbd5e).

[Abre Operator en español](https://huboptimus.dev/operator/?lang=es#product_intake).

## Flujo que funciona actualmente

1. Pega el texto completo de la fuente.
2. Si quieres conservar la procedencia, añade su URL pública; es opcional y no
   se recuperará ni verificará automáticamente.
3. Pulsa **Preparar borrador**.
4. Revisa los pasajes exactos propuestos.
5. Confirma que has revisado la selección.
6. Pulsa **Preparar borrador vinculado a la fuente**.
7. Revisa, corrige y guarda o exporta explícitamente el resultado.

El texto de la fuente no está limitado a 1.200 caracteres. Esa cifra
corresponde al contexto opcional del operador, no al contenido completo de la
fuente.

## Importación mediante URL

La importación automática de URLs no está operativa en el Operator público. El
comportamiento desplegado es deliberadamente inmediato y local:

- una URL sin texto no inicia ninguna petición y muestra el acceso previsto al
  Operator privado;
- una URL con texto conserva la URL exacta como atribución local no verificada;
- no introduzcas enlaces privados o firmados, tokens, contraseñas de un solo
  uso ni datos personales, porque una acción explícita de compartir puede
  incluir la URL;
- no presentes el contenido como verificado automáticamente.

## Qué produce

Operator prepara un borrador revisable con pasajes, afirmaciones, procedencia,
incertidumbres y siguientes acciones.

No ejecuta automáticamente el Semantic Engine, no verifica la verdad de una
noticia y no convierte una fuente en evidencia confirmada.

## Fuentes

- [Código del Operator](https://github.com/Voxterrae/HUB_Optimus/blob/c399c94e098058a723482001811c7d8491ebbd5e/site/operator/index.html)
- [Límite de idiomas e interfaz](https://github.com/Voxterrae/HUB_Optimus/blob/c399c94e098058a723482001811c7d8491ebbd5e/site/i18n/README.md)
- [RFC de intake controlado](https://github.com/Voxterrae/HUB_Optimus/blob/c399c94e098058a723482001811c7d8491ebbd5e/docs/rfc/operator_controlled_url_intake.md)
