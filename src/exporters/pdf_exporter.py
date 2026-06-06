"""
Exportador profesional de metrados a PDF con membrete, tabla formateada
y datos del ingeniero para entrega a cliente.
"""
from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.measurements import MetradoItem

# ---------------------------------------------------------------------------
# Datos del ingeniero (debe coincidir con excel_exporter.py)
# ---------------------------------------------------------------------------
INGENIERO = {
    "nombre": "Mauro Cruz Balladares",
    "cip": "130410",
    "dni": "43151426",
    "telefono": "987547728",
    "email": "mauro.cruz.balladares@gmail.com",
    "direccion": "Mz. G Lt 7 Urb. Virgen del Sol, Los Olivos, Lima",
    "ruc": "10431514261",
}


# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------
_STYLES = {
    "title": ParagraphStyle(
        "Title",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=6,
        textColor=colors.HexColor("#1f2937"),
    ),
    "subtitle": ParagraphStyle(
        "Subtitle",
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#6b7280"),
    ),
    "section": ParagraphStyle(
        "SectionHeader",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor("#374151"),
    ),
    "body": ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
    ),
    "info_label": ParagraphStyle(
        "InfoLabel",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#374151"),
    ),
    "info_value": ParagraphStyle(
        "InfoValue",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1f2937"),
    ),
    "footer": ParagraphStyle(
        "Footer",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#9ca3af"),
    ),
    "header_cell": ParagraphStyle(
        "HeaderCell",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.white,
    ),
    "data_cell": ParagraphStyle(
        "DataCell",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#1f2937"),
    ),
    "data_cell_right": ParagraphStyle(
        "DataCellRight",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#1f2937"),
    ),
    "data_cell_center": ParagraphStyle(
        "DataCellCenter",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1f2937"),
    ),
}


# ---------------------------------------------------------------------------
# Generación de PDF
# ---------------------------------------------------------------------------

def _header_footer(canvas, doc):
    """Dibuja encabezado y pie de página en cada página."""
    canvas.saveState()
    w, h = A4

    # Línea superior
    canvas.setStrokeColor(colors.HexColor("#1f2937"))
    canvas.setLineWidth(1.5)
    canvas.line(2 * cm, h - 1.5 * cm, w - 2 * cm, h - 1.5 * cm)

    # Encabezado: nombre del ingeniero
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.HexColor("#374151"))
    canvas.drawString(2 * cm, h - 1.3 * cm, f"{INGENIERO['nombre']} - CIP {INGENIERO['cip']}")

    # Línea inferior
    canvas.setStrokeColor(colors.HexColor("#d1d5db"))
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.5 * cm, w - 2 * cm, 1.5 * cm)

    # Pie de página
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#9ca3af"))
    canvas.drawString(2 * cm, 1.2 * cm, f"{INGENIERO['email']} | {INGENIERO['telefono']}")
    canvas.drawRightString(w - 2 * cm, 1.2 * cm, f"Pág. {doc.page}")

    canvas.restoreState()


def _build_info_table(proyecto: str, especialidad: str) -> Table:
    """Construye la tabla de información del proyecto."""
    data = [
        [
            Paragraph("Ingeniero:", _STYLES["info_label"]),
            Paragraph(INGENIERO["nombre"], _STYLES["info_value"]),
            Paragraph("Proyecto:", _STYLES["info_label"]),
            Paragraph(proyecto or "Por definir", _STYLES["info_value"]),
        ],
        [
            Paragraph("CIP:", _STYLES["info_label"]),
            Paragraph(INGENIERO["cip"], _STYLES["info_value"]),
            Paragraph("Especialidad:", _STYLES["info_label"]),
            Paragraph(especialidad or "General", _STYLES["info_value"]),
        ],
        [
            Paragraph("DNI:", _STYLES["info_label"]),
            Paragraph(INGENIERO["dni"], _STYLES["info_value"]),
            Paragraph("Fecha:", _STYLES["info_label"]),
            Paragraph(date.today().strftime("%d/%m/%Y"), _STYLES["info_value"]),
        ],
        [
            Paragraph("RUC:", _STYLES["info_label"]),
            Paragraph(INGENIERO["ruc"], _STYLES["info_value"]),
            Paragraph("Revisión:", _STYLES["info_label"]),
            Paragraph("00 - Preliminar", _STYLES["info_value"]),
        ],
    ]

    tbl = Table(data, colWidths=[3.5 * cm, 4.5 * cm, 3.5 * cm, 4.5 * cm])
    tbl.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f9fafb")),
            ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f9fafb")),
        ])
    )
    return tbl


def _build_metrado_table(items: list[MetradoItem]) -> Table:
    """Construye la tabla principal de metrados."""
    data = [[
        Paragraph("Partida", _STYLES["header_cell"]),
        Paragraph("Descripción", _STYLES["header_cell"]),
        Paragraph("Und", _STYLES["header_cell"]),
        Paragraph("Cantidad", _STYLES["header_cell"]),
        Paragraph("Conf.", _STYLES["header_cell"]),
        Paragraph("Fuente", _STYLES["header_cell"]),
    ]]

    for i, item in enumerate(items):
        bg = colors.white if i % 2 == 0 else colors.HexColor("#f9fafb")
        data.append([
            Paragraph(item.partida, _STYLES["data_cell_center"]),
            Paragraph(item.descripcion, _STYLES["data_cell"]),
            Paragraph(item.unidad, _STYLES["data_cell_center"]),
            Paragraph(f"{item.cantidad:,.3f}", _STYLES["data_cell_right"]),
            Paragraph(f"{item.confianza:.0%}", _STYLES["data_cell_center"]),
            Paragraph(item.fuente, _STYLES["data_cell"]),
        ])

    col_widths = [2.5 * cm, 6.0 * cm, 1.5 * cm, 2.5 * cm, 1.5 * cm, 2.0 * cm]
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    return tbl


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def build_pdf(items: list[MetradoItem],
              proyecto: str = "Sin proyecto",
              especialidad: str = "General") -> bytes:
    """Genera un PDF profesional con membrete y tabla de metrados.

    Args:
        items: Lista de MetradoItem.
        proyecto: Nombre del proyecto.
        especialidad: Especialidad.

    Returns:
        Bytes del archivo PDF.
    """
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    story = []

    # Título
    story.append(Paragraph("INFORME DE METRADOS", _STYLES["title"]))
    story.append(Paragraph(f"Sistema de Metrado Automático de Planos", _STYLES["subtitle"]))
    story.append(Spacer(1, 8))

    # Línea separadora
    story.append(Spacer(1, 2))

    # Información del proyecto
    story.append(Paragraph("Datos del Proyecto", _STYLES["section"]))
    story.append(_build_info_table(proyecto, especialidad))
    story.append(Spacer(1, 12))

    # Tabla de metrados
    if items:
        story.append(Paragraph("Metrado", _STYLES["section"]))
        story.append(_build_metrado_table(items))
    else:
        story.append(Paragraph("No se encontraron elementos metrables en el plano.", _STYLES["body"]))

    # Firma
    story.append(Spacer(1, 24))
    story.append(Paragraph("_________________________________", ParagraphStyle(
        "SignatureLine", fontSize=10, alignment=TA_CENTER, spaceBefore=12)))
    story.append(Paragraph(
        f"{INGENIERO['nombre']}<br/>"
        f"Ingeniero Civil - CIP {INGENIERO['cip']}",
        ParagraphStyle(
            "SignatureName",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#374151"),
        ),
    ))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    output.seek(0)
    return output.read()
