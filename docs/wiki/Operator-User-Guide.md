# Guía de uso de Operator

> **Estado:** prototipo público con revisión humana obligatoria.  
> **Última revisión:** 2026-08-02.  
> **Base auditada:** [`4400b0d`](https://github.com/Voxterrae/HUB_Optimus/commit/4400b0d778dc64779f9db9bd4cdb398a7d46a69b).

[Abre Operator en español](https://huboptimus.dev/operator/?lang=es#product_intake).

## Flujo que funciona actualmente

1. Deja completamente vacío el campo de URL.
2. Pega el texto de la fuente.
3. Pulsa **Preparar borrador**.
4. Revisa los pasajes exactos propuestos.
5. Confirma que has revisado la selección.
6. Pulsa **Preparar borrador vinculado a la fuente**.
7. Revisa, corrige y guarda o exporta explícitamente el resultado.

El texto de la fuente no está limitado a 1.200 caracteres. Esa cifra
corresponde al contexto opcional del operador, no al contenido completo de la
fuente.

## Importación mediante URL

La importación automática de URLs no está operativa en el Operator público.
Hasta que exista la frontera privada autenticada:

- borra la URL;
- pega el texto completo;
- conserva externamente la URL como referencia;
- no presentes el contenido como verificado automáticamente.

## Qué produce

Operator prepara un borrador revisable con pasajes, afirmaciones, procedencia,
incertidumbres y siguientes acciones.

No ejecuta automáticamente el Semantic Engine, no verifica la verdad de una
noticia y no convierte una fuente en evidencia confirmada.

## Fuentes

- [Código del Operator](https://github.com/Voxterrae/HUB_Optimus/blob/4400b0d778dc64779f9db9bd4cdb398a7d46a69b/site/operator/index.html)
- [Límite de idiomas e interfaz](https://github.com/Voxterrae/HUB_Optimus/blob/4400b0d778dc64779f9db9bd4cdb398a7d46a69b/site/i18n/README.md)
- [RFC de intake controlado](https://github.com/Voxterrae/HUB_Optimus/blob/4400b0d778dc64779f9db9bd4cdb398a7d46a69b/docs/rfc/operator_controlled_url_intake.md)
