"""
Tests para el procesador OCR (src/processors/ocr_processor.py).
"""
import tempfile
from pathlib import Path

import fitz
import pytest
from PIL import Image, ImageDraw

from src.processors.ocr_processor import (
    extract_ocr_measurements,
    is_tesseract_available,
    _is_scanned_pdf,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scanned_pdf(text_lines: list[str]) -> Path:
    """Crea un PDF simulado escaneado con texto dibujado como imagen."""
    from io import BytesIO
    height = 40 * len(text_lines) + 40
    img = Image.new("RGB", (500, height), "white")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(text_lines):
        draw.text((20, 20 + i * 40), line, fill="black")

    # Guardar como PNG en buffer
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    pdf_path = Path(tempfile.mktemp(suffix=".pdf"))
    doc = fitz.open()
    page = doc.new_page(width=500, height=height)
    page.insert_image(page.rect, stream=buf.read())
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOCRAvailability:
    def test_tesseract_available(self):
        """Verifica que Tesseract esté instalado."""
        assert is_tesseract_available(), (
            "Tesseract OCR debe estar instalado para este test. "
            "Descárgalo de: https://github.com/UB-Mannheim/tesseract/wiki"
        )


class TestScannedPDFDetection:
    def test_detect_scanned_pdf(self):
        path = _make_scanned_pdf(["12.50 m"])
        doc = fitz.open(path)
        try:
            assert _is_scanned_pdf(doc) is True
        finally:
            doc.close()
            path.unlink()


class TestExtractOCR:
    def test_basic_dimension(self):
        path = _make_scanned_pdf(["12.50 m"])
        try:
            results = extract_ocr_measurements(path)
            assert len(results) >= 1, "OCR debería encontrar al menos 1 dimensión"
        finally:
            path.unlink()

    def test_multiple_dimensions(self):
        path = _make_scanned_pdf([
            "MUROS PRIMER NIVEL",
            "12.50 m",
            "VENTANA V-01 2.40 x 1.50 m",
            "PISO PORCELANATO 45.20 m2",
        ])
        try:
            results = extract_ocr_measurements(path)
            assert len(results) >= 2
        finally:
            path.unlink()

    def test_empty_scanned_pdf(self):
        """PDF sin texto reconocible debe devolver lista vacía."""
        path = _make_scanned_pdf(["ABC", "XYZ"])
        try:
            results = extract_ocr_measurements(path)
            # Sin números con unidades → sin mediciones
            assert len(results) == 0
        finally:
            path.unlink()

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_ocr_measurements(Path("/no/existe.pdf"))
