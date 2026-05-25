# Plantillas de metrados

Esta carpeta define formatos base para generar tablas de metrados de manera consistente.

## Archivos

- `metrado_schema.json`: esquema oficial inicial para la hoja de sustento y la hoja resumen.
- `metrado_templates.json`: plantillas especificas por tipo de metrado y especialidad.
- `specialty_mapping.json`: mapa de clasificacion por especialidad, grupo normativo, palabras clave, plantilla aplicable y unidad por defecto.

## Criterio de uso

La aplicacion debe producir dos salidas:

1. `Sustento de metrados`: detalle por elemento medido, con dimensiones, fuente, formula y parcial.
2. `Resumen de metrados`: agrupacion final por especialidad, codigo de partida, partida y unidad.

El formato no debe improvisarse en cada ejecucion. La app puede dejar campos vacios cuando no tenga informacion suficiente, pero debe mantener las mismas columnas para facilitar revision, comparacion y exportacion a presupuesto.

## Plantillas especificas

Las referencias indican que el metrado cambia segun el area o tipo de partida. Por eso `metrado_templates.json` incluye formatos para:

- Metrado general.
- Movimiento de tierras.
- Concreto simple.
- Concreto armado.
- Encofrado y desencofrado.
- Acero / fierro.
- Albanileria / muros y tabiques.
- Acabados.
- Pisos y pavimentos.
- Instalaciones sanitarias.
- Instalaciones electricas y mecanicas.

La aplicacion debe elegir la plantilla segun la partida detectada o seleccionada por el usuario. Si no puede clasificarla, debe usar `metrado_general`.

## Clasificacion por especialidad

La clasificacion debe seguir este orden:

1. Especialidad: por ejemplo `estructuras`, `arquitectura`, `instalaciones_sanitarias`.
2. Grupo normativo: por ejemplo `OE.2`, `OE.3`, `OE.4`.
3. Palabras clave de partida: por ejemplo `concreto armado`, `encofrado`, `acero`, `tarrajeo`.
4. Plantilla aplicable: por ejemplo `concreto_armado`, `encofrado`, `acero_fierro`.
5. Unidad por defecto: por ejemplo `m3`, `m2`, `kg`, `und`.

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
