"""
Procesador OCR para planos escaneados (PDFs que son solo imágenes).

Convierte páginas de PDF en imágenes, aplica OCR con Tesseract
y busca patrones de dimensiones/cotas en el texto reconocido.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from src.log_utils import get_logger, format_exception
from src.measurements import Measurement

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuración de Tesseract
# ---------------------------------------------------------------------------
_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_TESSDATA_DIR = os.path.expanduser(
    r"~\AppData\Local\Tesseract-OCR\tessdata"
)

# Asegurar que Tesseract encuentra los datos de idioma
os.environ["TESSDATA_PREFIX"] = _TESSDATA_DIR

# Importar pytesseract (con captura de error si no está instalado)
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD
    _TESSERACT_AVAILABLE = True
except (ImportError, Exception) as exc:
    _TESSERACT_AVAILABLE = False
    _TESSERACT_ERROR = str(exc)
    logger.warning(f"Tesseract no disponible: {exc}")

from PIL import Image

# ---------------------------------------------------------------------------
# Patrones de dimensiones en español
# ---------------------------------------------------------------------------

_DIMENSION_PATTERNS = [
    # Patrón principal: número + unidad (m, cm, mm, mt, mts)
    re.compile(r"(\d+(?:[.,]\d+)?)\s*(m|mt|mts|cm|mm)\b", re.IGNORECASE),
    # Patrón: @3.50 o @12.5 (cotas con @)
    re.compile(r"@\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE),
    # Patrón de cotas en AutoCAD: ###### (números de 4+ dígitos cerca de líneas)
    re.compile(r"\b(\d{4,})\b"),
]

# Patrones de anotaciones (ignorar)
_ANNOTATION_PATTERNS = [
    re.compile(r"\b(?:NORTE|SUR|ESTE|OESTE|ESCALA|CORTE|DETALLE|ELEVACION|PLANTA|PRIMER NIVEL|SEGUNDO NIVEL)\b", re.IGNORECASE),
    re.compile(r"^\s*[A-ZÁÉÍÓÚÑ\s]{2,30}\s*$"),  # texto sin números = probable etiqueta
]


def _to_meters(value: float, unit: str) -> float:
    normalized = unit.lower()
    if normalized in {"m", "mt", "mts"}:
        return value
    if normalized == "cm":
        return value / 100.0
    if normalized == "mm":
        return value / 1000.0
    return value


def _is_scanned_pdf(doc) -> bool:
    """Detecta si un PDF escaneado (poco o ningún texto extraíble)."""
    total_chars = 0
    total_images = 0
    for page_index in range(min(doc.page_count, 5)):  # muestrear primeras 5 páginas
        page = doc[page_index]
        text = page.get_text("text") or ""
        total_chars += len(text.strip())
        total_images += len(page.get_images())
    # Si tiene imágenes y muy poco texto, es escaneado
    return total_images > 0 and total_chars < 100


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

def _ocr_page(page, psm: int = 3, lang: str = "spa+eng") -> str:
    """Aplica OCR a una página de PDF usando Tesseract.

    Args:
        page: Página de PyMuPDF (fitz.Page).
        psm: Modo de segmentación de página (3=automático, 6=bloque, 11=texto).
        lang: Idiomas para OCR (spa+eng para español + inglés).

    Returns:
        Texto reconocido.
    """
    if not _TESSERACT_AVAILABLE:
        raise RuntimeError(
            "Tesseract OCR no está disponible. "
            "Instala pytesseract y asegúrate de que Tesseract 5+ esté instalado."
        )

    # Renderizar página a imagen (200 DPI para equilibrio velocidad/calidad)
    pix = page.get_pixmap(dpi=200)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Aplicar OCR
    custom_config = f"--psm {psm} --oem 3"
    text = pytesseract.image_to_string(img, lang=lang, config=custom_config)
    return text


def _extract_dimensions_from_ocr(text: str, page_num: int) -> list[Measurement]:
    """Busca patrones de dimensiones en texto OCR.

    Args:
        text: Texto reconocido por OCR.
        page_num: Número de página.

    Returns:
        Lista de mediciones encontradas.
    """
    results: list[Measurement] = []
    seen_values: set[str] = set()

    for pattern in _DIMENSION_PATTERNS:
        for match in pattern.finditer(text):
            raw_value = match.group(1).replace(",", ".")
            full_match = match.group(0).strip()

            # Saltar anotaciones
            if any(ap.search(full_match) for ap in _ANNOTATION_PATTERNS):
                continue

            # Evitar duplicados cercanos
            dedup_key = f"{raw_value}_{page_num}"
            if dedup_key in seen_values:
                continue
            seen_values.add(dedup_key)

            try:
                value = float(raw_value)
            except ValueError:
                continue

            # Determinar unidad
            unit_text = match.group(2).lower() if len(match.groups()) >= 2 else "m"

            # Si es un número grande sin unidad (ej: 4500), asumir mm
            if unit_text == "m" and value > 100:
                # Podría ser mm malinterpretado
                quantity = value / 1000.0
                unit = "mm"
            else:
                quantity = _to_meters(value, unit_text)
                unit = "m"

            if quantity > 0 and quantity < 1000:  # filtrar valores absurdos
                results.append(
                    Measurement(
                        "OCR",
                        f"ocr_pagina_{page_num}",
                        "ocr_dimension",
                        quantity,
                        unit,
                        f"OCR: {full_match}",
                        0.55,  # confianza más baja que texto vectorial
                    )
                )

    return results


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def extract_ocr_measurements(path: Path) -> list[Measurement]:
    """Extrae mediciones de un PDF escaneado usando OCR.

    Args:
        path: Ruta al archivo PDF.

    Returns:
        Lista de mediciones encontradas vía OCR.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        RuntimeError: Si Tesseract no está disponible.
        ValueError: Si el PDF no se puede procesar.
    """
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    if not _TESSERACT_AVAILABLE:
        raise RuntimeError(
            "OCR no disponible. Tesseract no está instalado o configurado.\n"
            "Instálalo desde: https://github.com/UB-Mannheim/tesseract/wiki"
        )

    import fitz

    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise ValueError(f"No se pudo abrir el PDF: {exc}") from exc

    results: list[Measurement] = []

    try:
        if not _is_scanned_pdf(doc):
            logger.info(f"PDF {path.name} no parece escaneado, tiene texto extraíble")
            return results

        logger.info(f"PDF escaneado detectado: {path.name} ({doc.page_count} páginas)")
        total_pages = min(doc.page_count, 20)  # límite de 20 páginas para OCR

        for page_index in range(total_pages):
            try:
                page = doc[page_index]
                page_num = page_index + 1
                logger.debug(f"OCR página {page_num}/{total_pages}...")

                text = _ocr_page(page, psm=3, lang="spa+eng")
                page_results = _extract_dimensions_from_ocr(text, page_num)
                results.extend(page_results)

                logger.debug(f"  → {len(page_results)} dimensiones encontradas")
            except Exception as exc:
                logger.warning(f"Error OCR en página {page_index + 1}: {format_exception(exc)}")
                continue

    finally:
        doc.close()

    logger.info(f"OCR: {len(results)} dimensiones extraídas de {path.name}")
    return results


def is_tesseract_available() -> bool:
    """Verifica si Tesseract OCR está disponible."""
    return _TESSERACT_AVAILABLE
