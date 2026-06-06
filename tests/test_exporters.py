"""
Tests para los exportadores (src/exporters/).
"""
import pytest
from src.measurements import MetradoItem
from src.exporters.excel_exporter import build_excel, build_simple_excel
from src.exporters.pdf_exporter import build_pdf


# ---------------------------------------------------------------------------
# Fixture compartido
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_items():
    return [
        MetradoItem("ARQ-01", "Muros y tabiques", "m", 20.8, "DXF", 0.9),
        MetradoItem("ARQ-02", "Pisos y contrapisos", "m2", 45.2, "DWG", 0.85),
        MetradoItem("EST-01", "Columnas", "m2", 0.36, "DWG", 0.85),
        MetradoItem("ISS-01", "Red de agua fría", "m", 12.5, "DXF", 0.8),
    ]


# ---------------------------------------------------------------------------
# Tests Excel
# ---------------------------------------------------------------------------

class TestExcelExporter:
    def test_build_excel_returns_bytes(self, sample_items):
        result = build_excel(sample_items, "test.dxf", "Arquitectura")
        assert isinstance(result, bytes)
        assert len(result) > 1000

    def test_build_excel_with_defaults(self, sample_items):
        result = build_excel(sample_items)
        assert len(result) > 1000

    def test_build_simple_excel(self, sample_items):
        result = build_simple_excel(sample_items)
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_empty_items_excel(self):
        result = build_excel([], "vacio.dxf")
        assert len(result) > 500  # incluso vacío debe generar estructura Excel

    def test_many_items(self, sample_items):
        """Con pocos items no debería fallar."""
        result = build_excel(sample_items * 3, "multi.dxf")  # 12 items
        assert len(result) > 2000


# ---------------------------------------------------------------------------
# Tests PDF
# ---------------------------------------------------------------------------

class TestPDFExporter:
    def test_build_pdf_returns_bytes(self, sample_items):
        result = build_pdf(sample_items, "test.dxf", "Arquitectura")
        assert isinstance(result, bytes)
        assert len(result) > 500

    def test_build_pdf_with_defaults(self, sample_items):
        result = build_pdf(sample_items)
        assert len(result) > 500

    def test_empty_items_pdf(self):
        """PDF con items vacíos debe generar documento sin tabla."""
        result = build_pdf([], "vacio.dxf")
        assert len(result) > 500

    def test_single_item(self):
        result = build_pdf([
            MetradoItem("ARQ-01", "Solo un muro", "m", 10, "DXF", 0.9)
        ], "simple.dxf")
        assert len(result) > 500
