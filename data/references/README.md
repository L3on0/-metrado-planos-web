# Referencias tecnicas

Esta carpeta contiene documentos de referencia para construir y validar el sistema de metrados.

## Documentos incluidos

| Documento | PDF | TXT | JSON | Uso principal |
| --- | --- | --- | --- | --- |
| Manual LECTURA DE PLANOS Y METRADOS | Si | Si | Si | Contexto de lectura de planos y criterios generales de metrado. |
| norma_metrados | Si | Si | Si | Reglas, unidades y criterios normativos para metrados. |
| Costos_y_Presupuestos_CAPECO | Si | Si | Si | Relacion entre metrados, costos, presupuestos y analisis de partidas. |
| resumen_contexto_archivos_extraidos | No | Si | Si | Resumen general de los archivos extraidos y su uso dentro del proyecto. |

## Formato de extraccion

Los archivos `.txt` contienen texto plano separado por paginas.

Los archivos `.json` contienen:

- `source_file`: nombre del PDF original.
- `page_count`: cantidad total de paginas.
- `pages`: lista de paginas con `page_number`, dimensiones y texto extraido.

Estos archivos permitiran crear reglas de interpretacion, validar criterios de metrado y alimentar futuras funciones de busqueda o asistencia dentro de la aplicacion.
