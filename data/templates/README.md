# Plantillas de metrados

Esta carpeta define formatos base para generar tablas de metrados de manera consistente.

## Archivos

- `metrado_schema.json`: esquema oficial inicial para la hoja de sustento y la hoja resumen.

## Criterio de uso

La aplicacion debe producir dos salidas:

1. `Sustento de metrados`: detalle por elemento medido, con dimensiones, fuente, formula y parcial.
2. `Resumen de metrados`: agrupacion final por especialidad, codigo de partida, partida y unidad.

El formato no debe improvisarse en cada ejecucion. La app puede dejar campos vacios cuando no tenga informacion suficiente, pero debe mantener las mismas columnas para facilitar revision, comparacion y exportacion a presupuesto.

## Columnas clave

La hoja de sustento conserva el rastro de calculo:

- `especialidad`
- `codigo_partida`
- `partida`
- `ubicacion`
- `fuente`
- `descripcion_elemento`
- `numero_elementos`
- `largo`
- `ancho`
- `alto_espesor`
- `area`
- `volumen`
- `peso`
- `formula`
- `parcial`
- `unidad`
- `observaciones`
- `confianza`

La hoja resumen agrupa:

- `especialidad`
- `codigo_partida`
- `partida`
- `unidad`
- `cantidad_total`
- `fuentes`
- `observaciones`
- `confianza_promedio`
