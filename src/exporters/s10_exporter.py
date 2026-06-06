"""
Exportador de metrados a formatos compatibles con S10 y CSV.

S10 (http://s10.pe) es el software estándar de presupuestos en Perú.
Este módulo exporta metrados en formatos que pueden importarse
directamente en S10, Excel u hojas de cálculo.
"""
from __future__ import annotations

import csv
from datetime import date
from io import BytesIO, StringIO
from typing import Optional

from src.measurements import MetradoItem


# ---------------------------------------------------------------------------
# CSV (compatible con S10 / Excel)
# ---------------------------------------------------------------------------

def build_csv(items: list[MetradoItem],
              proyecto: str = "Sin proyecto",
              especialidad: str = "General") -> bytes:
    """Genera un archivo CSV en formato compatible con S10.

    Columnas estándar para importar a S10:
        - Código: Código de partida
        - Descripción: Descripción del item
        - Und: Unidad de medida
        - Metrado: Cantidad

    Args:
        items: Lista de MetradoItem.
        proyecto: Nombre del proyecto.
        especialidad: Especialidad.

    Returns:
        Bytes del archivo CSV (codificado UTF-8 BOM para Excel).
    """
    output = StringIO()
    writer = csv.writer(output)

    # Encabezado informativo (comentado para S10)
    writer.writerow(["# SAS Metrados - Exportación S10"])
    writer.writerow(["# Proyecto:", proyecto])
    writer.writerow(["# Especialidad:", especialidad])
    writer.writerow(["# Fecha:", date.today().strftime("%d/%m/%Y")])
    writer.writerow([])

    # Encabezado de columnas
    writer.writerow(["Código", "Descripción", "Und", "Metrado"])

    # Datos
    for item in items:
        writer.writerow([
            item.partida,
            item.descripcion,
            item.unidad,
            f"{item.cantidad:.3f}",
        ])

    # Resumen al final
    writer.writerow([])
    writer.writerow(["# Total de partidas:", str(len(items))])

    result = output.getvalue()
    # UTF-8 BOM para Excel en Windows
    return (b"\xef\xbb\xbf" + result.encode("utf-8"))


# ---------------------------------------------------------------------------
# S10 Text (formato de texto plano para presupuestos)
# ---------------------------------------------------------------------------

def build_s10(items: list[MetradoItem],
              proyecto: str = "Sin proyecto",
              especialidad: str = "General") -> bytes:
    """Genera un archivo de texto en formato S10 (.s10).

    Este formato puede importarse directamente en S10 2000+.
    Cada línea representa una partida con formato:
        CODIGO|DESCRIPCION|UNIDAD|METRADO|PRECIO|TOTAL

    Args:
        items: Lista de MetradoItem.
        proyecto: Nombre del proyecto.
        especialidad: Especialidad.

    Returns:
        Bytes del archivo .s10.
    """
    lines = [
        f"S10-MET v1.0",
        f"PROYECTO:{proyecto}",
        f"ESPECIALIDAD:{especialidad}",
        f"FECHA:{date.today().strftime('%d/%m/%Y')}",
        f"INGENIERO:Mauro Cruz Balladares - CIP 130410",
        f"PARTIDAS:{len(items)}",
        "#CODIGO|DESCRIPCION|UNIDAD|METRADO",
    ]

    for item in items:
        lines.append(
            f"{item.partida}|{item.descripcion}|{item.unidad}|{item.cantidad:.3f}"
        )

    lines.append(f"#FIN")

    result = "\n".join(lines) + "\n"
    return (b"\xef\xbb\xbf" + result.encode("utf-8"))


# ---------------------------------------------------------------------------
# Excel simple (para S10 / hoja de cálculo)
# ---------------------------------------------------------------------------

def build_s10_excel(items: list[MetradoItem],
                    proyecto: str = "Sin proyecto") -> bytes:
    """Genera un archivo Excel con formato de importación S10.

    Columnas: Código, Descripción, Und, Metrado, Precio (opcional).

    Args:
        items: Lista de MetradoItem.
        proyecto: Nombre del proyecto.

    Returns:
        Bytes del archivo .xlsx.
    """
    from io import BytesIO
    import pandas as pd

    data = [it.as_dict() for it in items]
    # Renombrar columnas para S10
    s10_data = [
        {
            "Código": row["partida"],
            "Descripción": row["descripcion"],
            "Und": row["unidad"],
            "Metrado": row["cantidad"],
            "Precio": "",  # opcional, lo completa el usuario en S10
            "Total": "",   # calculado automáticamente
        }
        for row in data
    ]

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(s10_data).to_excel(writer, sheet_name="Metrado S10", index=False)
        # Ajustar ancho de columnas
        for sheet in writer.book.worksheets:
            sheet.column_dimensions["A"].width = 14  # Código
            sheet.column_dimensions["B"].width = 50  # Descripción
            sheet.column_dimensions["C"].width = 8   # Und
            sheet.column_dimensions["D"].width = 14  # Metrado
            sheet.column_dimensions["E"].width = 12  # Precio
            sheet.column_dimensions["F"].width = 14  # Total

    output.seek(0)
    return output.read()
