"""
Clasificación inteligente de elementos de planos por capa y tipo.

Provee un mapeo extensivo de nombres de capa (patrones regex) a partidas
CAPECO/constructivas, más filtrado de elementos de referencia (cotas, ejes,
texto, hatch) que no deben incluirse en el metrado.
"""
from __future__ import annotations

import re
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Tipos de categoría
# ---------------------------------------------------------------------------
CAT_STRUCTURAL = "structural"
CAT_REFERENCE = "reference"


class LayerRule(NamedTuple):
    """Regla de clasificación para una capa."""

    pattern: re.Pattern  # regex compilado, case-insensitive
    partida: str
    descripcion: str
    category: str  # CAT_STRUCTURAL | CAT_REFERENCE
    order: int  # orden de evaluación (menor = primero)


# ---------------------------------------------------------------------------
# Reglas de clasificación por capa
# ---------------------------------------------------------------------------
# Ordenadas de más específicas a más genéricas.
# PRIMER MATCH GANA (se ejecutan en orden ascendente).
# ========================
# ESTRUCTURALES (incluir en metrado)
# ========================

_LAYER_RULES_DATA: list[tuple[str, str, str, str, int]] = [
    # ---- Arquitectura ----
    (r"\bMUROS?\b|WALL|ALBAÑILERIA|ALBA[^A-Z]*|TABIQUE|LADRILLO", "ARQ-01", "Muros y tabiques", CAT_STRUCTURAL, 10),
    (r"\bPISO\b|FLOOR|PAVIMENTO|CONTRAPISO|SOLADO", "ARQ-02", "Pisos y contrapisos", CAT_STRUCTURAL, 20),
    (r"ZOCALO|BASEBOARD|CONTRAZOCALO|C.ZOCALO", "ARQ-03", "Zócalos y contrazócalos", CAT_STRUCTURAL, 30),
    (r"TECHO|ROOF|CUBIERTA|CIELORRASO|F.C.R|FCR\b", "ARQ-04", "Techos y cielorrasos", CAT_STRUCTURAL, 40),
    (r"PUERTA|DOOR|VANO.*PUERTA|MARC(?:O|A)|PUERTA.*VENTANA", "ARQ-05", "Puertas y marcos", CAT_STRUCTURAL, 50),
    (r"VENTANA|WINDOW|VANO.*VENTANA|VIDRIO", "ARQ-06", "Ventanas y vidrios", CAT_STRUCTURAL, 60),
    (r"ESCALERA|STAIR|RAMP[A]?|GRADAS|PELDAÑO", "ARQ-07", "Escaleras y rampas", CAT_STRUCTURAL, 70),
    (r"BARANDA|PASAMANO|HANDRAIL|BARANDILLA", "ARQ-08", "Barandas y pasamanos", CAT_STRUCTURAL, 80),
    (r"REVOQUE|TARRAJEO|ENLUCIDO|YESO|REVESTIMIENTO", "ARQ-09", "Revoques y revestimientos", CAT_STRUCTURAL, 90),
    (r"PINTURA|PAINT|PINTADO|BARNIZ", "ARQ-10", "Pintura", CAT_STRUCTURAL, 100),
    (r"MAMPARA|MAMPA", "ARQ-11", "Mamparas", CAT_STRUCTURAL, 110),
    (r"CONTRAZOCALO|C.ZOC|CZOC", "ARQ-03", "Contrazócalos", CAT_STRUCTURAL, 120),

    # ---- Estructuras ----
    (r"COLUMNA|COLUMN|PILAR|PILOTE|CABEZAL", "EST-01", "Columnas", CAT_STRUCTURAL, 200),
    (r"VIGA|BEAM|VIGUETA|VIGA.*CORONA|VIGA.*SOLERA|DINTEL", "EST-02", "Vigas", CAT_STRUCTURAL, 210),
    (r"LOSA|SLAB|ALIGERADO|MACIZO", "EST-03", "Losas aligeradas / macizas", CAT_STRUCTURAL, 220),
    (r"CIMIENTO|FOUNDATION|ZAPATA|CIMENTACION|CORRIDA|CICLOPEO", "EST-04", "Cimentaciones", CAT_STRUCTURAL, 230),
    (r"SOBRECIMIENTO|SOBREC|SCIMIENTO", "EST-05", "Sobrecimientos", CAT_STRUCTURAL, 240),
    (r"MURO.*CONTENCION|M.CONT|CONTENCION|GAVION", "EST-06", "Muros de contención", CAT_STRUCTURAL, 250),
    (r"FALSO.*PISO|F.PISO|FPISO", "EST-07", "Falso piso", CAT_STRUCTURAL, 260),
    (r"ACERO|STEEL|REFUERZO|HIERRO|ARMADURA|FERRETERIA|F°|F\'", "EST-08", "Acero de refuerzo", CAT_STRUCTURAL, 270),

    # ---- Instalaciones Sanitarias ----
    (r"AGUA|WATER|TUBERIA.*AGUA|RED.*AGUA|MATRIZ.*AGUA", "ISS-01", "Red de agua", CAT_STRUCTURAL, 300),
    (r"DESAGUE|SEWER|TUBERIA.*DESAGUE|ALCANTARILLADO", "ISS-02", "Red de desagüe", CAT_STRUCTURAL, 310),
    (r"SANITARIO|SANITARY|APARATO.*SANITARIO|INODORO|LAVATORIO|URINARIO", "ISS-03", "Aparatos sanitarios", CAT_STRUCTURAL, 320),
    (r"TUBERIA|PIPE|TUBO|PVC", "ISS-04", "Tuberías en general", CAT_STRUCTURAL, 330),

    # ---- Instalaciones Eléctricas ----
    (r"ELECTRICO|ELECTRIC|ELEC\b|ILUMINACION|LIGHTING", "ISE-01", "Instalaciones eléctricas", CAT_STRUCTURAL, 400),
    (r"TOMA.*CORRIENTE|OUTLET|INTERRUPTOR|SWITCH", "ISE-02", "Tomacorrientes e interruptores", CAT_STRUCTURAL, 410),
    (r"CABLE|CABLEADO|WIRING|CONDUCTOR", "ISE-03", "Cableado", CAT_STRUCTURAL, 420),
    (r"TABLERO|PANEL|BOARD|DISTRIBUCION", "ISE-04", "Tableros eléctricos", CAT_STRUCTURAL, 430),

    # ---- Varios constructivos ----
    (r"JUNTA|JOINT|SELLO|SEAL", "VAR-01", "Juntas y sellos", CAT_STRUCTURAL, 500),
    (r"IMPERMEABILIZACION|WATERPROOF|MEMBRANA", "VAR-02", "Impermeabilización", CAT_STRUCTURAL, 510),
    (r"VEREDA|SIDEWALK|BALDOSA|LOZA.*PEATONAL", "VAR-03", "Veredas y baldosas", CAT_STRUCTURAL, 520),

    # ========================
    # REFERENCIA (NO incluir en metrado)
    # ========================

    (r"COTA|DIMENSION|ACOT|DIM[^E]|MEDIDA|DISTANCIA", "REF-01", "Cotas y dimensiones", CAT_REFERENCE, 1000),
    (r"EJE|AXIS|GRID|LINEA.*EJE|EJE.*(?:A|B|C|1|2|3)", "REF-02", "Ejes", CAT_REFERENCE, 1010),
    (r"TEXTO|TEXT|TXT\b|ROTULO|LETRA|LABEL|NOTA|NOTE|LTE[A-Z]?", "REF-03", "Textos y rótulos", CAT_REFERENCE, 1020),
    (r"HATCH|SOMBREADO|SHADE|HAT\b|PATRON", "REF-04", "Hatch y sombreado", CAT_REFERENCE, 1030),
    (r"CORTE|SECTION|DETALLE|DETAIL|VISTA|ELEVACION|ELEVATION", "REF-05", "Cortes y detalles", CAT_REFERENCE, 1040),
    (r"PORTICO|CUADRO|TABLE|LEYENDA|LEGEND|SIMBOLOGIA", "REF-06", "Cuadros y leyendas", CAT_REFERENCE, 1050),
    (r"NORTE|NORTH|ORIENTACION|ORIENTATION|COORDENADA", "REF-07", "Orientación y coordenadas", CAT_REFERENCE, 1060),
    (r"INDEFINIDO|DEFPOINTS|DEFPOINT|AUX|AUXILIAR|0\b|DEF$", "REF-08", "Capas auxiliares", CAT_REFERENCE, 1070),
]

# Compilar todas las reglas
LAYER_RULES: list[LayerRule] = [
    LayerRule(re.compile(p, re.IGNORECASE), partida, desc, cat, order)
    for p, partida, desc, cat, order in _LAYER_RULES_DATA
]

# Cache de clasificaciones ya resueltas
_classification_cache: dict[str, LayerRule] = {}


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def classify_layer(layer_name: str, default_partida: str = "GEN-01",
                   default_desc: str = "Elemento general",
                   default_category: str = CAT_STRUCTURAL) -> LayerRule:
    """Clasifica un nombre de capa contra las reglas conocidas.

    Args:
        layer_name: Nombre de la capa AutoCAD/DXF (ej: ``MUROS-PRIMER-NIVEL``).
        default_partida: Partida por defecto si no hay match.
        default_desc: Descripción por defecto.
        default_category: Categoría por defecto.

    Returns:
        LayerRule con la primera regla que matchea.
    """
    if not layer_name:
        return LayerRule(
            re.compile(".*"), default_partida, default_desc, default_category, 9999
        )

    cache_key = layer_name.strip().upper()
    if cache_key in _classification_cache:
        return _classification_cache[cache_key]

    for rule in LAYER_RULES:
        if rule.pattern.search(cache_key):
            _classification_cache[cache_key] = rule
            return rule

    fallback = LayerRule(
        re.compile(".*"), default_partida, default_desc, default_category, 9999
    )
    _classification_cache[cache_key] = fallback
    return fallback


def is_structural(layer_name: str) -> bool:
    """Determina si una capa es estructural (debe incluirse en metrado).

    Returns:
        True si la capa es estructural o no clasificada (inclusión por defecto).
        False si la capa es de referencia (cotas, ejes, texto, etc.).
    """
    return classify_layer(layer_name).category == CAT_STRUCTURAL


def classify_measurement(layer: str, element_type: str,
                         description: str = "") -> tuple[str, str, str]:
    """Clasifica una medición completa y devuelve (partida, descripción, categoría).

    Args:
        layer: Nombre de la capa.
        element_type: Tipo de entidad (line, polyline, dimension_text, etc.).
        description: Descripción opcional para mejorar la clasificación.

    Returns:
        Tupla (partida_code, descripcion, categoria).
    """
    rule = classify_layer(layer)

    # Si no hay match específico, intentar clasificar por tipo de elemento
    if rule.partida == "GEN-01":
        # Tipos de elemento que son claramente referencia
        if element_type in ("dimension_text", "text", "annotation"):
            return "REF-03", "Texto/Anotación", CAT_REFERENCE
        if element_type == "hatch":
            return "REF-04", "Hatch", CAT_REFERENCE

    return rule.partida, rule.descripcion, rule.category


# ---------------------------------------------------------------------------
# Utilidad: filtrar mediciones
# ---------------------------------------------------------------------------

def filter_structural(measurements: list) -> list:
    """Filtra una lista de objetos Measurement, quedándose solo con los
    que pertenecen a capas estructurales.

    Args:
        measurements: Lista de objetos con atributo ``.layer``.

    Returns:
        Lista filtrada (solo estructurales).
    """
    return [m for m in measurements if is_structural(m.layer)]


def filter_reference(measurements: list) -> list:
    """Inverso: devuelve solo los elementos de referencia.

    Útil para diagnóstico o para mostrar qué se excluyó.
    """
    return [m for m in measurements if not is_structural(m.layer)]
