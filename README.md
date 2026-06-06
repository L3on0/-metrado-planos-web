# Metrado Planos Web

Aplicacion local para subir planos, reconocer medidas principales y generar una tabla de metrados exportable a Excel y PDF.

## Alcance inicial

- DXF: lectura directa con `ezdxf` para lineas, polilineas y circulos.
- PDF: lectura vectorial/textual con `PyMuPDF`; extrae textos con formato de medida y longitudes de trazos.
- DWG: lectura mediante AutoCAD abierto usando `pyautocad`/COM. Requiere Windows + AutoCAD instalado.
- Exportacion: Excel (`openpyxl`) y PDF (`reportlab`).

## Instalar

```powershell
cd C:\Users\Mauro\metrado_planos_web
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecutar

```powershell
streamlit run app.py
```

## Notas tecnicas

- La deteccion automatica de metrados necesita escala confiable. Si el plano no trae unidades o escala, la app permite ingresar un factor manual.
- Para DWG, AutoCAD debe poder abrir el archivo en la misma maquina.
- La logica de partidas esta en `src/measurements.py`; ahi se pueden mapear capas como muros, pisos, zocalos, columnas, etc.
