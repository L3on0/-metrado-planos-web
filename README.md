# Metrado Planos Web

Aplicacion local para subir planos, reconocer medidas principales y generar tablas de metrados exportables a Excel y PDF.

El proyecto combina una interfaz web en Streamlit con procesadores de archivos de planos y documentos tecnicos de referencia para metrados, lectura de planos, costos y presupuestos.

## Objetivo

- Subir planos en formatos `DWG`, `DXF` y `PDF`.
- Extraer mediciones base desde entidades del plano o texto de cotas.
- Agrupar mediciones en partidas de metrado.
- Exportar resultados a Excel y PDF.
- Mantener documentos de referencia tecnicos para alimentar reglas, contexto y validaciones del sistema.

## Estructura

```text
.
|-- app.py
|-- requirements.txt
|-- src/
|   |-- measurements.py
|   |-- processors/
|   |   |-- autocad_processor.py
|   |   |-- dxf_processor.py
|   |   `-- pdf_processor.py
|   `-- exporters/
|       |-- excel_exporter.py
|       `-- pdf_exporter.py
|-- data/
|   |-- references/
|   `-- templates/
`-- outputs/
```

## Instalacion

Requisitos principales:

- Windows.
- Python 3.11 o superior.
- AutoCAD instalado para procesar archivos `DWG` con `pyautocad`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecucion

```powershell
streamlit run app.py
```

Luego abre la URL local que muestre Streamlit, normalmente:

```text
http://localhost:8501
```

## Librerias principales

- `streamlit`: interfaz web local.
- `pandas`: manejo de tablas.
- `openpyxl`: exportacion a Excel.
- `ezdxf`: lectura de planos `DXF`.
- `PyMuPDF`: lectura de texto y vectores desde `PDF`.
- `reportlab`: exportacion de reportes PDF.
- `pyautocad`: automatizacion de AutoCAD para lectura de `DWG`.
- `comtypes`: comunicacion COM requerida por AutoCAD en Windows.

## Referencias tecnicas

La carpeta `data/references/` contiene documentos base y extracciones en texto/JSON:

- `Manual LECTURA DE PLANOS Y METRADOS.pdf`
- `Manual LECTURA DE PLANOS Y METRADOS.txt`
- `Manual LECTURA DE PLANOS Y METRADOS.json`
- `norma_metrados.pdf`
- `norma_metrados.txt`
- `norma_metrados.json`
- `Costos_y_Presupuestos_CAPECO.pdf`
- `Costos_y_Presupuestos_CAPECO.txt`
- `Costos_y_Presupuestos_CAPECO.json`
- `resumen_contexto_archivos_extraidos.txt`
- `resumen_contexto_archivos_extraidos.json`

Los archivos `.txt` sirven para lectura rapida y busqueda manual. Los archivos `.json` conservan la extraccion hoja por hoja para que el sistema pueda usarlos como contexto estructurado.

## Plantillas de metrado

La carpeta `data/templates/` contiene el formato predeterminado de salida:

- `metrado_schema.json`: define la hoja de sustento, la hoja resumen, columnas, tipos de dato, unidades permitidas y reglas de agrupacion.
- `metrado_templates.json`: define formatos especificos por tipo de metrado, como concreto, encofrado, acero, acabados e instalaciones.
- `specialty_mapping.json`: clasifica partidas por especialidad, grupo normativo, palabras clave, plantilla y unidad por defecto.

La aplicacion debe mantener este formato como base para que los metrados sean revisables, comparables y exportables a presupuesto.

## Estado actual

Esta es una base inicial del proyecto. El reconocimiento de metrados ya separa responsabilidades por tipo de archivo, pero las reglas de partidas todavia deben calibrarse con planos reales, capas de AutoCAD, escalas y criterios de la norma de metrados.
