"""
Interfaz web Streamlit para el sistema de metrado de planos.

Todos los formatos (DXF, DWG, PDF) usan el mismo pipeline:
    upload → extract_measurements() → build_metrado() → build_excel() PDF
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st

from src.exporters.capeco_tables import (
    build_capeco_tables,
    build_formatted_capeco_excel,
)
from src.exporters.excel_exporter import build_excel, build_simple_excel
from src.exporters.pdf_exporter import build_pdf
from src.measurements import Measurement, MetradoItem, build_metrado, measurements_to_rows
from src.processors.autocad_processor import extract_dwg_measurements
from src.processors.dxf_processor import extract_dxf_measurements
from src.processors.pdf_processor import extract_pdf_measurements


SUPPORTED_TYPES = ["dwg", "dxf", "pdf"]
APP_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def save_upload(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix.lower()
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return Path(tmp.name)


def extract_measurements(file_path: Path, scale_factor: float) -> list[Measurement]:
    """Pipeline único: extrae mediciones de cualquier formato soportado."""
    suffix = file_path.suffix.lower()
    if suffix == ".dxf":
        return extract_dxf_measurements(file_path, scale_factor=scale_factor)
    if suffix == ".pdf":
        return extract_pdf_measurements(file_path, scale_factor=scale_factor)
    if suffix == ".dwg":
        return extract_dwg_measurements(file_path, scale_factor=scale_factor)
    raise ValueError(f"Formato no soportado: {suffix}")


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="SAS Metrados", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem;}
    div[data-testid="stMetric"] {background: #f8fafc; border: 1px solid #dbe3ea; padding: 10px; border-radius: 6px;}
    .stButton button {width: 100%; border-radius: 6px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("SAS Metrados")

with st.sidebar:
    st.header("Plano")
    uploaded = st.file_uploader("Subir DWG, DXF o PDF", type=SUPPORTED_TYPES, accept_multiple_files=False)
    st.caption(
        "💡 **Recomendación:** Los archivos **DXF** se procesan más rápido "
        "y **no requieren AutoCAD**. Si tu plano está en DWG, "
        "conviértelo a DXF desde AutoCAD (GUARDARCOMO → .dxf) "
        "o un visor gratuito."
    )
    scale_factor = st.number_input(
        "Factor de escala a metros",
        min_value=0.000001, value=1.0, step=0.01, format="%.6f",
    )
    specialty = st.selectbox(
        "Especialidad",
        ["Arquitectura", "Estructuras", "Instalaciones sanitarias", "Instalaciones electricas"],
    )
    run_analysis = st.button("Analizar plano", type="primary")

if uploaded is None:
    st.info("Sube un plano para iniciar el análisis.")
    st.stop()

file_path = save_upload(uploaded)
st.caption(f"Archivo cargado: `{uploaded.name}`")

if run_analysis:
    st.session_state["last_file"] = str(file_path)
    st.session_state["last_name"] = uploaded.name
    try:
        st.session_state["measurements"] = extract_measurements(file_path, scale_factor)
        # Construir metrado automáticamente
        items = build_metrado(st.session_state["measurements"])
        st.session_state["capeco_metrado_items"] = items
    except Exception as exc:
        st.error(f"No se pudo analizar el archivo: {exc}")
        st.stop()

tabs = st.tabs(["Diagnóstico", "Metrado", "Mediciones base", "Descargas"])

# ---- Tab 0: Diagnóstico ----
with tabs[0]:
    if "measurements" in st.session_state:
        ms = st.session_state["measurements"]
        from src.classification import filter_reference, classify_layer

        structural = [m for m in ms if classify_layer(m.layer).category == "structural"]
        reference = [m for m in ms if classify_layer(m.layer).category != "structural"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mediciones totales", len(ms))
        c2.metric("Estructurales", len(structural))
        c3.metric("Referencia (excluídas)", len(reference))
        c4.metric("Partidas", len(st.session_state.get("capeco_metrado_items", [])))

        # Desglose por capa
        st.subheader("Distribución por capa")
        from collections import Counter
        layer_counts = Counter(m.layer for m in ms)
        layer_df = pd.DataFrame(
            layer_counts.most_common(20),
            columns=["Capa", "Entidades"],
        )
        layer_df["Clasificación"] = layer_df["Capa"].apply(
            lambda l: f"{classify_layer(l).partida} - {classify_layer(l).descripcion}"
        )
        st.dataframe(layer_df, use_container_width=True, hide_index=True)

        # Capas no reconocidas
        unknown = [
            (layer, count) for layer, count in layer_counts.items()
            if classify_layer(layer).partida == "GEN-01"
        ]
        if unknown:
            st.warning(
                f"⚠️ **{len(unknown)} capas no reconocidas:** "
                + ", ".join(f"`{l}` ({c})" for l, c in unknown[:10])
            )
    else:
        st.info("Presiona `Analizar plano` para ver el diagnóstico.")

# ---- Tab 1: Metrado (editable) ----
with tabs[1]:
    if "capeco_metrado_items" not in st.session_state:
        st.info("Presiona `Analizar plano` para generar el metrado.")
    else:
        items = st.session_state["capeco_metrado_items"]

        # Inicializar estado de correcciones
        if "metrado_excluded" not in st.session_state:
            st.session_state["metrado_excluded"] = set()
        if "metrado_overrides" not in st.session_state:
            st.session_state["metrado_overrides"]: dict[int, dict] = {}
        if "metrado_manual_items" not in st.session_state:
            st.session_state["metrado_manual_items"]: list[MetradoItem] = []

        # ---- Mostrar items con controles ----
        st.subheader(f"Metrado ({len(items)} partidas)")

        for i, item in enumerate(items):
            excluded = i in st.session_state["metrado_excluded"]
            overrides = st.session_state["metrado_overrides"].get(i, {})

            cols = st.columns([0.5, 1.5, 3, 1, 1.5, 1])
            with cols[0]:
                excl = st.checkbox("", value=excluded, key=f"excl_{i}",
                                   label_visibility="collapsed")
                if excl and not excluded:
                    st.session_state["metrado_excluded"].add(i)
                elif not excl and excluded:
                    st.session_state["metrado_excluded"].discard(i)
            with cols[1]:
                partida_opts = [
                    "ARQ-01", "ARQ-02", "ARQ-03", "ARQ-04", "ARQ-05", "ARQ-06",
                    "ARQ-07", "ARQ-08", "ARQ-09", "ARQ-10", "ARQ-11",
                    "EST-01", "EST-02", "EST-03", "EST-04", "EST-05", "EST-06", "EST-07", "EST-08",
                    "ISS-01", "ISS-02", "ISS-03", "ISS-04",
                    "ISE-01", "ISE-02", "ISE-03", "ISE-04",
                    "VAR-01", "VAR-02", "VAR-03",
                ]
                pid = overrides.get("partida", item.partida)
                try:
                    idx = partida_opts.index(pid)
                except ValueError:
                    partida_opts.insert(0, pid)
                    idx = 0
                new_pid = st.selectbox(
                    "", partida_opts, index=idx, key=f"pid_{i}",
                    label_visibility="collapsed",
                )
                if new_pid != item.partida:
                    st.session_state["metrado_overrides"].setdefault(i, {})["partida"] = new_pid
                elif "partida" in st.session_state["metrado_overrides"].get(i, {}):
                    del st.session_state["metrado_overrides"][i]["partida"]

            with cols[2]:
                new_desc = st.text_input(
                    "", value=overrides.get("descripcion", item.descripcion),
                    key=f"desc_{i}", label_visibility="collapsed",
                )
                if new_desc != item.descripcion:
                    st.session_state["metrado_overrides"].setdefault(i, {})["descripcion"] = new_desc
            with cols[3]:
                new_qty = st.number_input(
                    "", value=overrides.get("cantidad", item.cantidad),
                    format="%.3f", key=f"qty_{i}", label_visibility="collapsed",
                )
                if new_qty != item.cantidad:
                    st.session_state["metrado_overrides"].setdefault(i, {})["cantidad"] = new_qty
            with cols[4]:
                st.markdown(f"**{item.unidad}**")
            with cols[5]:
                apply_corrections_func = st.button("🔄", key=f"apply_{i}",
                                                    help="Aplicar cambios a esta fila",
                                                    use_container_width=True)
            if excluded:
                st.markdown(f"<span style='color:#ef4444;font-size:0.8em'>❌ Excluido</span>",
                            unsafe_allow_html=True)

        # ---- Botón recalcular ----
        has_changes = (
            st.session_state["metrado_excluded"]
            or st.session_state["metrado_overrides"]
            or st.session_state["metrado_manual_items"]
        )
        if has_changes:
            if st.button("🔄 Recalcular metrado con correcciones",
                         type="primary", use_container_width=True):
                from src.measurements import apply_corrections
                corrected = apply_corrections(
                    items,
                    st.session_state["metrado_excluded"],
                    st.session_state["metrado_overrides"],
                )
                corrected.extend(st.session_state["metrado_manual_items"])
                st.session_state["capeco_metrado_items"] = corrected
                st.rerun()

        # ---- Añadir partida manual ----
        st.divider()
        with st.expander("➕ Añadir partida manual"):
            man_pid = st.selectbox("Partida", partida_opts, key="man_pid")
            man_desc = st.text_input("Descripción", key="man_desc")
            man_qty = st.number_input("Cantidad", min_value=0.0, step=0.01, key="man_qty")
            man_unit = st.selectbox("Unidad", ["m", "m2", "und", "kg", "glb"], key="man_unit")
            if st.button("Añadir al metrado", use_container_width=True):
                manual = MetradoItem(
                    partida=man_pid,
                    descripcion=man_desc or "Partida manual",
                    unidad=man_unit,
                    cantidad=man_qty,
                    fuente="Manual",
                    confianza=1.0,
                )
                st.session_state["metrado_manual_items"].append(manual)
                all_items = list(items) + st.session_state["metrado_manual_items"]
                st.session_state["capeco_metrado_items"] = all_items
                st.rerun()

# ---- Tab 2: Mediciones base ----
with tabs[2]:
    if "measurements" in st.session_state:
        raw_df = pd.DataFrame(measurements_to_rows(st.session_state["measurements"]))
        if not raw_df.empty:
            st.dataframe(raw_df, use_container_width=True, hide_index=True)
        else:
            st.info("Todas las mediciones fueron filtradas como referencia.")
    else:
        st.info("Sube un plano y presiona `Analizar plano` para ver mediciones.")

# ---- Tab 3: Descargas ----
with tabs[3]:
    if "capeco_metrado_items" in st.session_state:
        items = st.session_state["capeco_metrado_items"]
        proyecto = uploaded.name

        # Excel profesional
        excel_bytes = build_excel(
            items=items,
            proyecto=proyecto,
            especialidad=specialty,
            escala=scale_factor,
        )
        st.download_button(
            "📥 Descargar Excel profesional (.xlsx)",
            excel_bytes,
            file_name=f"metrado_{Path(uploaded.name).stem}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        # PDF profesional
        pdf_bytes = build_pdf(
            items=items,
            proyecto=proyecto,
            especialidad=specialty,
        )
        st.download_button(
            "📥 Descargar PDF profesional",
            pdf_bytes,
            file_name=f"metrado_{Path(uploaded.name).stem}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        # Excel simple
        simple_bytes = build_simple_excel(items)
        st.download_button(
            "Descargar Excel simple (vista rápida)",
            simple_bytes,
            file_name=f"metrado_simple_{Path(uploaded.name).stem}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.info("Sube un plano y presiona `Analizar plano` para habilitar descargas.")
