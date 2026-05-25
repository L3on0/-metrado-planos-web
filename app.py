from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st

from src.exporters.excel_exporter import build_excel
from src.exporters.pdf_exporter import build_pdf
from src.measurements import Measurement, build_metrado, measurements_to_rows
from src.processors.autocad_processor import extract_dwg_measurements
from src.processors.dxf_processor import extract_dxf_measurements
from src.processors.pdf_processor import extract_pdf_measurements


SUPPORTED_TYPES = ["dwg", "dxf", "pdf"]


def save_upload(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix.lower()
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return Path(tmp.name)


def extract_measurements(file_path: Path, scale_factor: float) -> list[Measurement]:
    suffix = file_path.suffix.lower()
    if suffix == ".dxf":
        return extract_dxf_measurements(file_path, scale_factor=scale_factor)
    if suffix == ".pdf":
        return extract_pdf_measurements(file_path, scale_factor=scale_factor)
    if suffix == ".dwg":
        return extract_dwg_measurements(file_path, scale_factor=scale_factor)
    raise ValueError(f"Formato no soportado: {suffix}")


st.set_page_config(page_title="Metrado de Planos", layout="wide")

st.title("Metrado de Planos")

left, right = st.columns([0.36, 0.64], gap="large")

with left:
    uploaded = st.file_uploader(
        "Subir plano",
        type=SUPPORTED_TYPES,
        accept_multiple_files=False,
    )
    scale_factor = st.number_input(
        "Factor de escala a metros",
        min_value=0.000001,
        value=1.0,
        step=0.01,
        format="%.6f",
        help="Ejemplo: si 1 unidad del dibujo equivale a 0.01 m, usar 0.01.",
    )
    include_raw = st.checkbox("Mostrar mediciones base", value=True)

with right:
    if uploaded is None:
        st.info("Sube un archivo DWG, DXF o PDF para iniciar el reconocimiento.")
    else:
        try:
            file_path = save_upload(uploaded)
            measurements = extract_measurements(file_path, scale_factor=scale_factor)
            metrado = build_metrado(measurements)

            st.subheader("Tabla de metrados")
            metrado_df = pd.DataFrame([item.as_dict() for item in metrado])
            st.dataframe(metrado_df, use_container_width=True, hide_index=True)

            excel_bytes = build_excel(metrado_df, measurements_to_rows(measurements))
            pdf_bytes = build_pdf(metrado)

            export_col_1, export_col_2 = st.columns(2)
            with export_col_1:
                st.download_button(
                    "Descargar Excel",
                    excel_bytes,
                    file_name="metrado_planos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            with export_col_2:
                st.download_button(
                    "Descargar PDF",
                    pdf_bytes,
                    file_name="metrado_planos.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            if include_raw:
                st.subheader("Mediciones base")
                raw_df = pd.DataFrame(measurements_to_rows(measurements))
                st.dataframe(raw_df, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"No se pudo procesar el plano: {exc}")
