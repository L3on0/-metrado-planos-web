"""
Tests para el módulo de mediciones (src/measurements.py).
"""
import pytest
from src.measurements import (
    Measurement,
    MetradoItem,
    build_metrado,
    measurements_to_rows,
    classify,
)


class TestMeasurement:
    """Tests del dataclass Measurement."""

    def test_create_basic(self):
        m = Measurement("DXF", "MUROS", "line", 12.5, "m", "Muro exterior", 0.9)
        assert m.source == "DXF"
        assert m.layer == "MUROS"
        assert m.quantity == 12.5
        assert m.confidence == 0.9

    def test_default_confidence(self):
        m = Measurement("DXF", "MUROS", "line", 10, "m", "")
        assert m.confidence == 0.7  # valor por defecto


class TestMetradoItem:
    """Tests del dataclass MetradoItem."""

    def test_as_dict(self):
        item = MetradoItem("ARQ-01", "Muros", "m", 20.5, "DXF", 0.9)
        d = item.as_dict()
        assert d["partida"] == "ARQ-01"
        assert d["cantidad"] == 20.5
        assert d["confianza"] == 0.90

    def test_cantidad_rounding(self):
        """Python banker's rounding: 20.5555 → 20.555 (floating point)."""
        item = MetradoItem("ARQ-01", "Muros", "m", 20.5555, "DXF", 0.9)
        assert abs(item.as_dict()["cantidad"] - 20.555) < 0.001


class TestBuildMetrado:
    """Tests de agrupación de mediciones en metrado."""

    def test_empty_list(self):
        items = build_metrado([])
        assert items == []

    def test_single_measurement(self):
        ms = [Measurement("DXF", "MUROS", "line", 12.5, "m", "", 0.9)]
        items = build_metrado(ms)
        assert len(items) == 1
        assert items[0].partida == "ARQ-01"
        assert items[0].cantidad == 12.5

    def test_grouping_by_partida(self):
        ms = [
            Measurement("DXF", "MUROS", "line", 10, "m", "", 0.9),
            Measurement("DXF", "MUROS", "line", 8.3, "m", "", 0.9),
        ]
        items = build_metrado(ms)
        assert len(items) == 1  # se agrupan
        assert items[0].cantidad == 18.3  # 10 + 8.3

    def test_multiple_partidas(self):
        ms = [
            Measurement("DXF", "MUROS", "line", 10, "m", "", 0.9),
            Measurement("DXF", "COLUMNAS", "closed_polyline", 0.36, "m2", "", 0.85),
        ]
        items = build_metrado(ms)
        assert len(items) == 2

    def test_reference_filtered_out_by_default(self):
        ms = [
            Measurement("DXF", "MUROS", "line", 10, "m", "", 0.9),
            Measurement("DXF", "COTA-DIMENSION", "line", 5, "m", "", 0.5),
        ]
        items = build_metrado(ms)
        assert len(items) == 1  # COTA excluida

    def test_reference_included_when_flag_set(self):
        ms = [
            Measurement("DXF", "MUROS", "line", 10, "m", "", 0.9),
            Measurement("DXF", "COTA-DIMENSION", "line", 5, "m", "", 0.5),
        ]
        items = build_metrado(ms, include_reference=True)
        assert len(items) == 2  # COTA incluida

    def test_dimension_text_excluded(self):
        """Elementos dimension_text deben ser excluidos (REF-03)."""
        ms = [
            Measurement("PDF", "pagina_1", "dimension_text", 3.5, "m", "", 0.75),
            Measurement("DXF", "MUROS", "line", 10, "m", "", 0.9),
        ]
        items = build_metrado(ms)
        assert len(items) == 1
        assert items[0].partida != "REF-03"


class TestMeasurementsToRows:
    """Tests de conversión a filas planas."""

    def test_basic_conversion(self):
        ms = [Measurement("DXF", "MUROS", "line", 10, "m", "Test", 0.9)]
        rows = measurements_to_rows(ms)
        assert len(rows) == 1
        assert rows[0]["capa"] == "MUROS"
        assert rows[0]["partida"] == "ARQ-01"

    def test_rows_filter_references(self):
        ms = [
            Measurement("DXF", "MUROS", "line", 10, "m", "", 0.9),
            Measurement("DXF", "COTA", "line", 5, "m", "", 0.5),
        ]
        rows = measurements_to_rows(ms)
        assert len(rows) == 1  # solo MUROS

    def test_rows_include_references(self):
        ms = [
            Measurement("DXF", "MUROS", "line", 10, "m", "", 0.9),
            Measurement("DXF", "COTA", "line", 5, "m", "", 0.5),
        ]
        rows = measurements_to_rows(ms, include_reference=True)
        assert len(rows) == 2


class TestClassify:
    """Tests de la función classify() que envuelve classify_measurement."""

    def test_classify_structural(self):
        m = Measurement("DXF", "MUROS", "line", 10, "m", "", 0.9)
        p, d, c = classify(m)
        assert p == "ARQ-01"

    def test_classify_reference(self):
        m = Measurement("DXF", "COTA-DIMENSION", "line", 5, "m", "", 0.5)
        p, d, c = classify(m)
        assert "REF" in p
