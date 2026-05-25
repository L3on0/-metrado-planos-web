import re
from pathlib import Path

import fitz

from src.measurements import Measurement


DIMENSION_RE = re.compile(r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>m|mt|mts|cm|mm)\b", re.IGNORECASE)


def _to_meters(value: float, unit: str) -> float:
    normalized = unit.lower()
    if normalized in {"m", "mt", "mts"}:
        return value
    if normalized == "cm":
        return value / 100.0
    if normalized == "mm":
        return value / 1000.0
    return value


def extract_pdf_measurements(path: Path, scale_factor: float = 1.0) -> list[Measurement]:
    doc = fitz.open(path)
    results: list[Measurement] = []

    for page_index, page in enumerate(doc, start=1):
        text = page.get_text("text")
        for match in DIMENSION_RE.finditer(text):
            raw = match.group("value").replace(",", ".")
            unit = match.group("unit")
            quantity = _to_meters(float(raw), unit)
            results.append(
                Measurement(
                    "PDF",
                    f"pagina_{page_index}",
                    "dimension_text",
                    quantity,
                    "m",
                    f"Cota textual: {match.group(0)}",
                    0.75,
                )
            )

        drawings = page.get_drawings()
        for drawing in drawings:
            for item in drawing.get("items", []):
                if item[0] != "l":
                    continue
                start, end = item[1], item[2]
                dx = end.x - start.x
                dy = end.y - start.y
                length = ((dx * dx + dy * dy) ** 0.5) * scale_factor
                if length > 0:
                    results.append(
                        Measurement(
                            "PDF",
                            f"pagina_{page_index}",
                            "vector_line",
                            length,
                            "m",
                            "Linea vectorial de PDF",
                            0.45,
                        )
                    )

    return results
