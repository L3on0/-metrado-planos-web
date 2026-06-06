"""
Procesador de archivos PDF de planos.

Extrae mediciones desde:
- Texto de dimensiones (cotas escritas como "12.5 m")
- Líneas vectoriales del dibujo
- OCR para PDFs escaneados (con Tesseract)
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz

from src.classification import is_structural
from src.log_utils import get_logger, format_exception
from src.measurements import Measurement
from src.processors.ocr_processor import (
    extract_ocr_measurements,
    is_tesseract_available,
    _is_scanned_pdf as _check_scanned,
)

logger = get_logger(__name__)

DIMENSION_RE = re.compile(r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>m|mt|mts|cm|mm)\b", re.IGNORECASE)
PDF_LAYER = "pdf_plano"


def _to_meters(value: float, unit: str) -> float:
    normalized = unit.lower()
    if normalized in {"m", "mt", "mts"}:
        return value
    if normalized == "cm":
        return value / 100.0
    if normalized == "mm":
        return value / 1000.0
    return value


def _is_annotation_text(text: str) -> bool:
    """Detecta si un texto parece ser anotación (no medición)."""
    upper = text.strip().upper()
    # Textos típicos de anotación
    annotations = {
        "N", "S", "E", "O", "ESC", "ESCALA",
        "NORTE", "SUR", "ESTE", "OESTE",
        "PRIMER NIVEL", "SEGUNDO NIVEL", "TERCER NIVEL",
        "CORTE", "ELEVACION", "DETALLE", "PLANTA",
    }
    if upper in annotations:
        return True
    # Textos que contienen solo letras (probablemente etiquetas)
    if re.match(r"^[A-ZÁÉÍÓÚÑ\s]{2,20}$", upper) and not re.search(r"\d", upper):
        return True
    return False


def extract_pdf_measurements(path: Path, scale_factor: float = 1.0) -> list[Measurement]:
    """Extrae mediciones de un archivo PDF.

    Args:
        path: Ruta al archivo .pdf.
        scale_factor: Factor de conversión a metros.

    Returns:
        Lista de mediciones extraídas.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si el PDF está vacío, es escaneado o no se puede leer.
    """
    if not path.exists():
        raise FileNotFoundError(f"Archivo PDF no encontrado: {path}")

    if path.stat().st_size == 0:
        raise ValueError(f"El archivo PDF está vacío: {path.name}")

    # Intentar abrir el PDF
    try:
        doc = fitz.open(path)
    except Exception as exc:
        logger.error(f"Error al abrir PDF {path.name}: {format_exception(exc)}")
        raise ValueError(
            f"No se pudo abrir el archivo PDF '{path.name}'. "
            "Puede estar corrupto o protegido."
        ) from exc

    results: list[Measurement] = []
    page_count = 0

    try:
        if doc.page_count == 0:
            raise ValueError(f"El PDF '{path.name}' no contiene páginas.")
        page_count = doc.page_count

        if doc.page_count > 50:
            logger.warning(f"PDF con {doc.page_count} páginas - puede ser lento de procesar")

        for page_index in range(doc.page_count):
            try:
                page = doc[page_index]
                page_num = page_index + 1

                # --- Detectar PDF escaneado y aplicar OCR ---
                text = page.get_text("text") or ""

                if page_index == 0 and not text.strip():
                    images = page.get_images()
                    if images:
                        logger.info(f"PDF escaneado detectado en {path.name} "
                                    f"({len(images)} imágenes por página). "
                                    "Aplicando OCR...")
                        # Cerrar el doc actual y delegar al OCR processor
                        doc.close()
                        ocr_results = extract_ocr_measurements(path)
                        if not ocr_results:
                            logger.warning(f"OCR no encontró dimensiones en {path.name}")
                            return []
                        logger.info(f"OCR: {len(ocr_results)} dimensiones encontradas")
                        return ocr_results

                # --- Extraer dimensiones textuales ---
                for match in DIMENSION_RE.finditer(text):
                    raw = match.group("value").replace(",", ".")
                    unit = match.group("unit")
                    full_text = match.group(0).strip()

                    if _is_annotation_text(full_text):
                        continue

                    quantity = _to_meters(float(raw), unit)
                    if quantity > 0:
                        results.append(
                            Measurement(
                                PDF_LAYER,
                                f"pagina_{page_num}",
                                "dimension_text",
                                quantity,
                                "m",
                                f"Cota textual: {full_text}",
                                0.75,
                                coord_x=float(page_num) * 100,
                                coord_y=0.0,
                            )
                        )

                # --- Extraer líneas vectoriales ---
                drawings = page.get_drawings()
                for drawing in drawings:
                    try:
                        for item in drawing.get("items", []):
                            if item[0] != "l":
                                continue
                            start, end = item[1], item[2]
                            dx = end.x - start.x
                            dy = end.y - start.y
                            length = ((dx * dx + dy * dy) ** 0.5) * scale_factor
                            if length > 0.001:  # ignorar líneas minúsculas
                                cx = (start.x + end.x) / 2
                                cy = (start.y + end.y) / 2
                                results.append(
                                    Measurement(
                                        PDF_LAYER,
                                        f"pagina_{page_num}",
                                        "vector_line",
                                        length,
                                        "m",
                                        "Linea vectorial de PDF",
                                        0.45,
                                        coord_x=cx,
                                        coord_y=cy,
                                    )
                                )
                    except Exception as exc:
                        logger.debug(f"Error procesando drawing en pág {page_num}: "
                                     f"{format_exception(exc)}")
                        continue

            except Exception as exc:
                logger.warning(f"Error procesando página {page_index + 1} de {path.name}: "
                              f"{format_exception(exc)}")
                continue

    finally:
        doc.close()

    if not results:
        logger.warning(f"No se extrajeron mediciones de {path.name}. "
                       "Puede ser un PDF escaneado (solo imágenes) sin texto vectorial.")

    logger.info(f"PDF {path.name}: {len(results)} mediciones extraídas "
                f"({page_count} páginas)")
    return results
