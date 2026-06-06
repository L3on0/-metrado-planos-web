"""
Procesador de archivos DWG via pyautocad (AutoCAD COM).

Requiere AutoCAD instalado y ejecutándose.
"""
from __future__ import annotations

from pathlib import Path

from src.classification import is_structural, classify_layer, infer_unit
from src.log_utils import get_logger, format_exception
from src.measurements import Measurement

logger = get_logger(__name__)

# Tipos de entidad AutoCAD que nunca son estructurales
_REFERENCE_OBJECTS = frozenset({
    "AcDbText", "AcDbMText", "AcDbDimension", "AcDbHatch",
    "AcDbBlockReference", "AcDbViewport", "AcDbRay", "AcDbXline",
})


def _centroid_from_entity(entity) -> tuple[float, float]:
    """Extrae el centroide aproximado de una entidad AutoCAD."""
    try:
        if hasattr(entity, "Centroid"):
            c = entity.Centroid
            return float(c[0]), float(c[1])
        if entity.ObjectName.endswith("AcDbLine"):
            s = entity.StartPoint
            e = entity.EndPoint
            return (float(s[0]) + float(e[0])) / 2, (float(s[1]) + float(e[1])) / 2
    except Exception:
        pass
    return 0.0, 0.0


def extract_dwg_measurements(path: Path, scale_factor: float = 1.0) -> list[Measurement]:
    """Extrae mediciones de un archivo DWG via AutoCAD COM."""
    if not path.exists():
        raise FileNotFoundError(f"Archivo DWG no encontrado: {path}")
    if path.suffix.lower() != ".dwg":
        logger.warning(f"Extensión inesperada: {path.suffix} (se esperaba .dwg)")

    try:
        from pyautocad import Autocad
    except ImportError as exc:
        raise RuntimeError("pip install pyautocad comtypes") from exc

    try:
        acad = Autocad(create_if_not_exists=True)
        _ = acad.app.Name
    except Exception as exc:
        raise ConnectionError("AutoCAD no disponible. Usa DXF.") from exc

    try:
        document = acad.app.Documents.Open(str(path))
    except Exception as exc:
        raise ValueError(f"No se pudo abrir {path.name} en AutoCAD.") from exc

    results: list[Measurement] = []
    errors = 0
    total_entities = 0

    try:
        for entity in document.ModelSpace:
            total_entities += 1
            try:
                object_name = getattr(entity, "ObjectName", "")
                layer = getattr(entity, "Layer", "0")
                if not is_structural(layer) or object_name in _REFERENCE_OBJECTS:
                    continue

                cx, cy = _centroid_from_entity(entity)

                if object_name.endswith("AcDbLine"):
                    s, e = entity.StartPoint, entity.EndPoint
                    dx = e[0] - s[0]
                    dy = e[1] - s[1]
                    length = ((dx * dx + dy * dy) ** 0.5) * scale_factor
                    if length > 0:
                        p = classify_layer(layer).partida
                        u = infer_unit(p, "line")
                        results.append(Measurement("DWG", layer, "line", length, u,
                                                   "Linea AutoCAD", 0.9, cx, cy))

                elif object_name.endswith("AcDbPolyline") or object_name.endswith("AcDb2dPolyline"):
                    p = classify_layer(layer).partida
                    length = float(entity.Length) * scale_factor
                    area = float(getattr(entity, "Area", 0) or 0) * (scale_factor**2)
                    has_area = area > 0

                    if has_area and infer_unit(p, "closed_polyline") == "und":
                        results.append(Measurement("DWG", layer, "closed_polyline", 1.0, "und",
                                                   "Elemento contabilizado", 0.85, cx, cy))
                    else:
                        if length > 0:
                            pu = infer_unit(p, "polyline")
                            pq = 1.0 if pu == "und" else length
                            results.append(Measurement("DWG", layer, "polyline", pq, pu,
                                                       "Polilinea AutoCAD", 0.85, cx, cy))
                        if has_area:
                            au = infer_unit(p, "closed_polyline")
                            aq = 1.0 if au == "und" else area
                            results.append(Measurement("DWG", layer, "closed_polyline", aq, au,
                                                       "Area AutoCAD", 0.85, cx, cy))

                elif object_name.endswith("AcDbCircle"):
                    p = classify_layer(layer).partida
                    radius = float(entity.Radius) * scale_factor
                    perimeter = 2 * 3.141592653589793 * radius
                    area = 3.141592653589793 * radius * radius
                    pu = infer_unit(p, "circle_perimeter")
                    au = infer_unit(p, "circle_area")
                    pqty = 1.0 if pu == "und" else perimeter
                    aqty = 1.0 if au == "und" else area
                    if pu == "und" or pqty > 0:
                        results.append(Measurement("DWG", layer, "circle_perimeter", pqty, pu,
                                                   "Circulo AutoCAD", 0.8, cx, cy))
                    if au == "und" or aqty > 0:
                        results.append(Measurement("DWG", layer, "circle_area", aqty, au,
                                                   "Area circulo AutoCAD", 0.8, cx, cy))

            except Exception:
                errors += 1
                if errors <= 5:
                    logger.warning(f"Error en entidad {total_entities}")
                continue
    except Exception as exc:
        raise RuntimeError(f"Error al leer {path.name}.") from exc
    finally:
        try:
            document.Close(False)
        except Exception:
            pass

    logger.info(f"DWG {path.name}: {len(results)} mediciones ({total_entities} entidades, {errors} errores)")
    return results
