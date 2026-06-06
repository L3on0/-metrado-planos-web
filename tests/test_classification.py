"""
Tests para el módulo de clasificación (src/classification.py).
"""
import pytest
from src.classification import (
    classify_layer,
    is_structural,
    classify_measurement,
    filter_structural,
    filter_reference,
    CAT_REFERENCE,
    CAT_STRUCTURAL,
)
from src.measurements import Measurement


class TestClassifyLayer:
    """Tests de clasificación por nombre de capa."""

    def test_muros(self):
        r = classify_layer("MUROS-1ER-NIVEL")
        assert r.partida == "ARQ-01"
        assert r.category == CAT_STRUCTURAL

    def test_muro_singular(self):
        r = classify_layer("MURO")
        assert r.partida == "ARQ-01"

    def test_pisos(self):
        r = classify_layer("PISO-PRINCIPAL")
        assert r.partida == "ARQ-02"

    def test_cotas(self):
        r = classify_layer("COTA-DIMENSION")
        assert r.partida == "REF-01"
        assert r.category == CAT_REFERENCE

    def test_ejes(self):
        r = classify_layer("EJE-01")
        assert r.partida == "REF-02"

    def test_texto(self):
        r = classify_layer("TEXTO-ROTULO")
        assert r.partida == "REF-03"

    def test_hatch(self):
        r = classify_layer("HATCH-PATRON")
        assert r.partida == "REF-04"

    def test_columnas(self):
        r = classify_layer("COLUMNAS-C1")
        assert r.partida == "EST-01"

    def test_vigas(self):
        r = classify_layer("VIGAS-PRINCIPALES")
        assert r.partida == "EST-02"

    def test_losas(self):
        r = classify_layer("LOSA-ALIGERADA")
        assert r.partida == "EST-03"

    def test_cimientos(self):
        r = classify_layer("CIMIENTO-CORRIDO")
        assert r.partida == "EST-04"

    def test_puertas(self):
        r = classify_layer("PUERTAS-PA-01")
        assert r.partida == "ARQ-05"

    def test_ventanas(self):
        r = classify_layer("VENTANAS-V-01")
        assert r.partida == "ARQ-06"

    def test_escaleras(self):
        r = classify_layer("ESCALERA-1")
        assert r.partida == "ARQ-07"

    def test_agua(self):
        r = classify_layer("RED-AGUA-FRIA")
        assert r.partida == "ISS-01"

    def test_desague(self):
        r = classify_layer("DESAGUE-DOMESTICO")
        assert r.partida == "ISS-02"

    def test_electrico(self):
        r = classify_layer("ILUMINACION-GENERAL")
        assert r.partida == "ISE-01"

    def test_defpoints(self):
        r = classify_layer("DEFPOINTS")
        assert r.partida == "REF-08"

    def test_capa_0(self):
        r = classify_layer("0")
        assert r.partida == "REF-08"

    def test_capa_desconocida(self):
        r = classify_layer("ZZ_LAYER_XYZ_123")
        assert r.partida == "GEN-01"
        assert r.category == CAT_STRUCTURAL  # default es estructural

    def test_layer_vacia(self):
        r = classify_layer("")
        assert r.partida == "GEN-01"

    def test_layer_none(self):
        r = classify_layer(None)  # type: ignore
        assert r.partida == "GEN-01"


class TestIsStructural:
    """Tests del filtro estructural/referencia."""

    @pytest.mark.parametrize("layer,expected", [
        ("MUROS", True),
        ("PISOS", True),
        ("COLUMNAS-C1", True),
        ("VENTANAS", True),
        ("COTA-DIMENSION", False),
        ("EJE-01", False),
        ("TEXTO-ROTULO", False),
        ("HATCH-TEST", False),
        ("CORTE-A-A", False),
        ("DEFPOINTS", False),
        ("0", False),
    ])
    def test_is_structural(self, layer, expected):
        assert is_structural(layer) == expected


class TestFilterStructural:
    """Tests de filtrado de mediciones."""

    def test_filter_keeps_structural(self):
        ms = [
            Measurement("DXF", "MUROS", "line", 10, "m", "", 0.9),
            Measurement("DXF", "COLUMNAS", "line", 5, "m", "", 0.9),
        ]
        filtered = filter_structural(ms)
        assert len(filtered) == 2

    def test_filter_removes_reference(self):
        ms = [
            Measurement("DXF", "MUROS", "line", 10, "m", "", 0.9),
            Measurement("DXF", "COTA", "line", 5, "m", "", 0.5),
            Measurement("DXF", "EJE-01", "line", 20, "m", "", 0.3),
        ]
        filtered = filter_structural(ms)
        assert len(filtered) == 1
        assert filtered[0].layer == "MUROS"

    def test_filter_reference_inverse(self):
        ms = [
            Measurement("DXF", "MUROS", "line", 10, "m", "", 0.9),
            Measurement("DXF", "COTA", "line", 5, "m", "", 0.5),
        ]
        refs = filter_reference(ms)
        assert len(refs) == 1
        assert refs[0].layer == "COTA"


class TestClassifyMeasurement:
    """Tests de clasificación completa (capa + tipo de elemento)."""

    def test_dimension_text_fallback(self):
        """Elementos dimension_text sin capa obvia deben ser REF-03."""
        p, d, c = classify_measurement("pagina_1", "dimension_text")
        assert p == "REF-03"
        assert c == CAT_REFERENCE

    def test_structural_by_layer(self):
        p, d, c = classify_measurement("MUROS", "line")
        assert p == "ARQ-01"
        assert c == CAT_STRUCTURAL


class TestCache:
    """Tests del cache de clasificación (rendimiento)."""

    def test_cache_reuse(self):
        from src.classification import _classification_cache
        _classification_cache.clear()
        r1 = classify_layer("MUROS")
        r2 = classify_layer("MUROS")
        assert r1 is r2  # misma instancia del cache
