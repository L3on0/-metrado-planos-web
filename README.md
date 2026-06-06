# SAS Metrados

Aplicación web para metrado automático de planos de construcción a partir de archivos DWG, DXF y PDF. Extrae mediciones, clasifica por partidas CAPECO y exporta a Excel profesional, PDF con membrete y formato S10.

## Requisitos

### Mínimos (DXF + PDF + OCR)
- Python 3.11+
- Tesseract OCR 5+ (para PDFs escaneados), instalado en `C:\Program Files\Tesseract-OCR\`
- Idiomas: spa (español) + eng (inglés)

### Opcionales
- AutoCAD (para procesar DWG via pyautocad COM)

## Instalación rápida

```bash
# Clonar
git clone https://github.com/L3on0/-metrado-planos-web.git
cd -metrado-planos-web

# Crear entorno virtual
python -m venv .venv
source .venv/Scripts/activate  # Windows git-bash

# Instalar dependencias
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

Abrir `http://localhost:8501`

## Docker

```bash
docker compose up -d
```

Abrir `http://localhost:8501`

> Nota: Docker no soporta procesamiento DWG (requiere AutoCAD COM en Windows).

## Estructura del proyecto

```
├── app.py                          ← Interfaz Streamlit
├── Dockerfile                      ← Imagen Docker
├── docker-compose.yml
├── requirements.txt
├── logs/                           ← Logs de ejecución
├── outputs/                        ← Archivos de muestra generados
├── data/
│   ├── references/                 ← Documentos técnicos de referencia
│   └── templates/                  ← Plantillas Excel CAPECO
└── src/
    ├── classification.py           ← 39 reglas de clasificación por capa
    ├── measurements.py             ← Modelos + build_metrado + filtros
    ├── log_utils.py                ← Logging centralizado
    ├── processors/
    │   ├── dxf_processor.py        ← DXF via ezdxf
    │   ├── pdf_processor.py        ← PDF texto + vectores + OCR fallback
    │   ├── ocr_processor.py        ← Tesseract OCR spa+eng
    │   └── autocad_processor.py    ← DWG via pyautocad COM
    └── exporters/
        ├── excel_exporter.py       ← Excel CAPECO profesional
        ├── pdf_exporter.py         ← PDF con membrete y firma
        ├── s10_exporter.py         ← CSV, S10, Excel S10
        └── capeco_tables.py        ← Tablas CAPECO (legacy)
```

## Pipeline de procesamiento

Todos los formatos (DXF, DWG, PDF) usan el mismo pipeline:

```
upload → extract_measurements() → build_metrado() → build_excel() / build_pdf()
```

1. **Extracción**: El procesador correspondiente extrae líneas, polilíneas, círculos y cotas del archivo
2. **Clasificación**: `classification.py` asigna cada elemento a una partida CAPECO según su capa
3. **Filtrado**: Se excluyen elementos de referencia (cotas, ejes, texto, hatch)
4. **Filtro de ruido**: Se eliminan elementos demasiado pequeños (< 0.10 m, < 0.01 m²) y duplicados
5. **Asignación de unidades**: Puertas/ventanas/columnas → und, muros → m, pisos → m²
6. **Exportación**: Excel profesional, PDF con membrete, CSV/S10

## Clasificación por capa

El módulo `classification.py` contiene 39 reglas que clasifican nombres de capa en partidas:

| Patrón de capa | Partida | Descripción |
|---|---|---|
| MUROS, WALL, ALBAÑILERIA | ARQ-01 | Muros y tabiques |
| PISO, FLOOR, PAVIMENTO | ARQ-02 | Pisos y contrapisos |
| PUERTA, DOOR, VANO | ARQ-05 | Puertas y marcos |
| VENTANA, WINDOW | ARQ-06 | Ventanas y vidrios |
| COLUMNA, COLUMN, PILAR | EST-01 | Columnas |
| VIGA, BEAM | EST-02 | Vigas |
| COTA, DIMENSION, ACOT | REF-01 | Cotas (excluído) |
| TEXTO, TEXT, ROTULO | REF-03 | Texto (excluído) |

Las capas no reconocidas se clasifican como GEN-01 (Elemento general) y se muestran como advertencia en la UI.

## Tests

```bash
pytest tests/ -v
# 102 tests, ~6s
```

## Licencia

Uso personal. Proyecto desarrollado por Mauro Cruz Balladares - CIP 130410.
