"""
Procesador de archivos DXF.

Extrae mediciones de entidades DXF (LINE, LWPOLYLINE, POLYLINE, CIRCLE)
filtrando por capa estructural y tipo de entidad.
"""
from __future__ import annotations

import os
from pathlib import Path

from src.classification import is_structural, classify_layer, infer_unit
from src.log_utils import get_logger, format_exception
from src.measurements import Measurement

logger = get_logger(__name__)

os.environ.setdefault("EZDXF_CACHE_DIR", str(Path(__file__).resolve().parents[2] / "data" / "ezdxf_cache"))
import ezdxf


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

_REFERENCE_DXF_TYPES = frozenset({
    "DIMENSION", "TEXT", "MTEXT", "HATCH", "ATTDEF", "ATTRIB",
    "INSERT", "VIEWPORT", "RAY", "XLINE", "POINT",
})


def _should_skip_entity(dxftype: str, layer: str) -> bool:
    """Determina si una entidad DXF debe ser ignorada."""
    if dxftype in _REFERENCE_DXF_TYPES:
        return True
    return not is_structural(layer)


# ---------------------------------------------------------------------------
# Geometría
# ---------------------------------------------------------------------------

def _polyline_length(points: list[tuple[float, float]]) -> float:
    length = 0.0
    for start, end in zip(points, points[1:]):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length += (dx * dx + dy * dy) ** 0.5
    return length


def _polygon_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    ring = points + [points[0]]
    for start, end in zip(ring, ring[1:]):
        area += start[0] * end[1] - end[0] * start[1]
    return abs(area) / 2.0


# ---------------------------------------------------------------------------
# Extracción principal
# ---------------------------------------------------------------------------

def extract_dxf_measurements(path: Path, scale_factor: float = 1.0) -> list[Measurement]:
    """Extrae mediciones de un archivo DXF.

    Args:
        path: Ruta al archivo .dxf.
        scale_factor: Factor de conversión a metros.

    Returns:
        Lista de mediciones extraídas. Vacía si el archivo no es válido.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si el archivo no es un DXF válido o está vacío.
    """
    # Validar que el archivo existe
    if not path.exists():
        raise FileNotFoundError(f"Archivo DXF no encontrado: {path}")

    if path.stat().st_size == 0:
        raise ValueError(f"El archivo DXF está vacío: {path.name}")

    # Validar extensión
    if path.suffix.lower() != ".dxf":
        logger.warning(f"Extensión inesperada: {path.suffix} (se esperaba .dxf)")

    # Leer el documento
    try:
        doc = ezdxf.readfile(str(path))
    except ezdxf.DXFStructureError as exc:
        logger.error(f"Error de estructura DXF en {path.name}: {format_exception(exc)}")
        raise ValueError(
            f"El archivo DXF '{path.name}' tiene una estructura inválida. "
            "Asegúrate de que sea un DXF válido (no un DWG renombrado)."
        ) from exc
    except ezdxf.DXFVersionError as exc:
        logger.error(f"Versión DXF no soportada en {path.name}: {format_exception(exc)}")
        raise ValueError(
            f"La versión del DXF '{path.name}' no es soportada. "
            "Guárdalo como DXF 2010 o anterior desde AutoCAD."
        ) from exc
    except IOError as exc:
        logger.error(f"Error de E/S al leer DXF {path.name}: {format_exception(exc)}")
        raise ValueError(f"No se pudo leer el archivo DXF '{path.name}'.") from exc

    try:
        msp = doc.modelspace()
    except Exception as exc:
        logger.error(f"Error al acceder al modelspace de {path.name}: {format_exception(exc)}")
        raise ValueError(f"El archivo DXF '{path.name}' no tiene un modelspace válido.") from exc

    results: list[Measurement] = []
    errors = 0

    for entity in msp:
        try:
            dxftype = entity.dxftype()
            layer = getattr(entity.dxf, "layer", "0")

            if _should_skip_entity(dxftype, layer):
                continue

            if dxftype == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                dx = end.x - start.x
                dy = end.y - start.y
                length = ((dx * dx + dy * dy) ** 0.5) * scale_factor
                if length > 0:
                    partida = classify_layer(layer).partida
                    unit = infer_unit(partida, "line")
                    results.append(
                        Measurement("DXF", layer, "line", length, unit, "Linea detectada", 0.9)
                    )

            elif dxftype in {"LWPOLYLINE", "POLYLINE"}:
                if dxftype == "LWPOLYLINE":
                    points = [(point[0], point[1]) for point in entity.get_points()]
                    is_closed = entity.closed
                else:
                    points = [(vertex.dxf.location.x, vertex.dxf.location.y) for vertex in entity.vertices]
                    is_closed = entity.is_closed

                if len(points) >= 2:
                    partida = classify_layer(layer).partida
                    length = _polyline_length(points)
                    if is_closed:
                        length += _polyline_length([points[-1], points[0]]) if len(points) > 1 else 0.0
                        area = _polygon_area(points) * (scale_factor**2)
                        if area > 0:
                            area_unit = infer_unit(partida, "closed_polyline")
                            area_qty = 1.0 if area_unit == "und" else area
                            results.append(
                                Measurement("DXF", layer, "closed_polyline", area_qty, area_unit,
                                            "Polilinea cerrada", 0.85)
                            )
                    # Para elementos contables (und), no crear medición de perímetro
                    if not (is_closed and infer_unit(partida, "closed_polyline") == "und"):
                        poly_unit = infer_unit(partida, "polyline")
                        poly_qty = 1.0 if poly_unit == "und" else length * scale_factor
                        results.append(
                            Measurement("DXF", layer, "polyline", poly_qty, poly_unit,
                                        "Polilinea detectada", 0.85)
                        )

            elif dxftype == "CIRCLE":
                partida = classify_layer(layer).partida
                radius = entity.dxf.radius * scale_factor
                perimeter = 2 * 3.141592653589793 * radius
                area = 3.141592653589793 * radius * radius
                perm_unit = infer_unit(partida, "circle_perimeter")
                area_unit = infer_unit(partida, "circle_area")
                perm_qty = 1.0 if perm_unit == "und" else perimeter
                area_qty = 1.0 if area_unit == "und" else area
                if perm_unit == "und" or perm_qty > 0:
                    results.append(
                        Measurement("DXF", layer, "circle_perimeter", perm_qty, perm_unit,
                                    "Perimetro de circulo", 0.8)
                    )
                if area_unit == "und" or area_qty > 0:
                    results.append(
                        Measurement("DXF", layer, "circle_area", area_qty, area_unit,
                                    "Area de circulo", 0.8)
                    )

        except Exception as exc:
            errors += 1
            if errors <= 5:
                logger.warning(f"Error procesando entidad {dxftype} en capa {layer}: "
                               f"{format_exception(exc)}")
            continue

    if errors > 0:
        logger.info(f"{errors} entidades no pudieron procesarse en {path.name}")

    if not results:
        logger.warning(f"No se extrajeron mediciones de {path.name} "
                       f"(sin entidades metrables después de filtrar)")

    logger.info(f"DXF {path.name}: {len(results)} mediciones extraídas ({errors} errores)")
    return results
