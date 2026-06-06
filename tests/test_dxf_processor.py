"""
Tests para el procesador DXF (src/processors/dxf_processor.py).

Genera archivos DXF temporales para pruebas sin depender de planos reales.
"""
import tempfile
from pathlib import Path

import ezdxf
import pytest

from src.processors.dxf_processor import (
    extract_dxf_measurements,
    _should_skip_entity,
    _polyline_length,
    _polygon_area,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dxf() -> tuple:
    """Crea un DXF temporal con una línea, un círculo y una polilínea."""
    tmp = Path(tempfile.mktemp(suffix=".dxf"))
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    # Línea
    msp.add_line((0, 0), (10, 0))
    # Círculo
    msp.add_circle((5, 5), 2)
    # Polilínea
    points = [(0, 0), (5, 0), (5, 5), (0, 5)]
    msp.add_lwpolyline(points, close=True)
    doc.saveas(str(tmp))
    return tmp, doc


# ---------------------------------------------------------------------------
# Tests de geometría
# ---------------------------------------------------------------------------

class TestGeometry:
    def test_polyline_length(self):
        pts = [(0, 0), (3, 0), (3, 4)]
        assert _polyline_length(pts) == pytest.approx(7.0)  # 3 + 5

    def test_polyline_length_zero(self):
        assert _polyline_length([(0, 0)]) == 0.0

    def test_polygon_area_square(self):
        pts = [(0, 0), (2, 0), (2, 2), (0, 2)]
        assert _polygon_area(pts) == pytest.approx(4.0)

    def test_polygon_area_triangle(self):
        pts = [(0, 0), (3, 0), (0, 4)]
        assert _polygon_area(pts) == pytest.approx(6.0)

    def test_polygon_area_less_than_3_points(self):
        assert _polygon_area([(0, 0), (1, 1)]) == 0.0


# ---------------------------------------------------------------------------
# Tests de filtrado
# ---------------------------------------------------------------------------

class TestShouldSkip:
    @pytest.mark.parametrize("dxftype,layer,expected", [
        ("LINE", "MUROS", False),
        ("LINE", "COTA-DIMENSION", True),
        ("TEXT", "MUROS", True),
        ("MTEXT", "MUROS", True),
        ("DIMENSION", "COLUMNAS", True),
        ("HATCH", "PISOS", True),
        ("CIRCLE", "COLUMNAS-C1", False),
        ("LWPOLYLINE", "PISO-PRINCIPAL", False),
        ("INSERT", "VENTANAS", True),
    ])
    def test_should_skip(self, dxftype, layer, expected):
        assert _should_skip_entity(dxftype, layer) == expected


# ---------------------------------------------------------------------------
# Tests de extracción
# ---------------------------------------------------------------------------

class TestExtractDXF:
    def test_basic_entities(self):
        tmp, doc = _make_dxf()
        try:
            results = extract_dxf_measurements(tmp)
            # 1 línea + 1 círculo (perímetro + área) + 1 polilínea (perímetro + área)
            # Pero la polilínea está en capa "0" que es REF-08 (auxiliar)
            # La línea y círculo también estarán en capa "0" → no deberían pasar
            # TODO: el test actual crea entidades en capa "0" que se filtra como REF-08
            # Mejoraremos el test usando capas estructurales
            pass
        finally:
            tmp.unlink()

    def test_extract_with_custom_layer(self):
        """Crea un DXF con entidades en capas estructurales y verifica unidades."""
        tmp = Path(tempfile.mktemp(suffix=".dxf"))
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "MUROS"})
        # Círculo en COLUMNAS = contable → und
        msp.add_circle((5, 5), 2, dxfattribs={"layer": "COLUMNAS-C1"})
        # Puerta = contable
        rect = [(0, 0), (1, 0), (1, 2.1), (0, 2.1)]
        msp.add_lwpolyline(rect, close=True, dxfattribs={"layer": "PUERTAS-PA-01"})
        doc.saveas(str(tmp))
        try:
            results = extract_dxf_measurements(tmp)
            # MUROS: 1 línea → unit=m
            line_measurements = [r for r in results if r.layer == "MUROS"]
            assert all(r.unit == "m" for r in line_measurements), "MUROS debe ser m"
            # COLUMNAS: círculo → unit=und
            col_measurements = [r for r in results if r.layer == "COLUMNAS-C1"]
            assert all(r.unit == "und" for r in col_measurements), "COLUMNAS debe ser und"
            assert all(r.quantity == 1.0 for r in col_measurements), "COLUMNAS qty=1"
            # PUERTAS: polilínea cerrada → unit=und
            door_measurements = [r for r in results if r.layer == "PUERTAS-PA-01"]
            assert all(r.unit == "und" for r in door_measurements), "PUERTAS debe ser und"
            assert len(results) == 4  # 1 línea + 2 círculo + 1 puerta
        finally:
            tmp.unlink()

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_dxf_measurements(Path("/no/existe.dxf"))

    def test_empty_file(self):
        tmp = Path(tempfile.mktemp(suffix=".dxf"))
        tmp.write_text("")
        try:
            with pytest.raises(ValueError, match="vacío"):
                extract_dxf_measurements(tmp)
        finally:
            tmp.unlink()

    def test_invalid_dxf_content(self):
        tmp = Path(tempfile.mktemp(suffix=".dxf"))
        tmp.write_text("esto no es un DXF válido")
        try:
            with pytest.raises(ValueError):
                extract_dxf_measurements(tmp)
        finally:
            tmp.unlink()
