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


def extract_dwg_measurements(path: Path, scale_factor: float = 1.0) -> list[Measurement]:
    """Extrae mediciones de un archivo DWG via AutoCAD COM.

    Prefiere DXF sobre DWG siempre que sea posible, ya que DXF se procesa
    sin dependencias externas. DWG requiere AutoCAD instalado y ejecutándose.

    Args:
        path: Ruta al archivo .dwg.
        scale_factor: Factor de conversión a metros.

    Returns:
        Lista de mediciones extraídas.

    Raises:
        RuntimeError: Si pyautocad no está instalado.
        ConnectionError: Si AutoCAD no está disponible o no responde.
            Este error incluye una sugerencia clara de usar DXF.
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si el archivo no es un DWG válido.
    """
    if not path.exists():
        raise FileNotFoundError(f"Archivo DWG no encontrado: {path}")

    if path.suffix.lower() != ".dwg":
        logger.warning(f"Extensión inesperada: {path.suffix} (se esperaba .dwg)")

    # Importar pyautocad (con mensaje claro si falta)
    try:
        from pyautocad import Autocad
    except ImportError as exc:
        raise RuntimeError(
            "pyautocad no está instalado. Ejecuta: pip install pyautocad comtypes"
        ) from exc

    # Conectar a AutoCAD
    try:
        acad = Autocad(create_if_not_exists=True)
        # Verificar que la conexión funciona
        _ = acad.app.Name
    except Exception as exc:
        logger.error(f"Conexión a AutoCAD falló: {format_exception(exc)}")
        raise ConnectionError(
            "No se pudo conectar a AutoCAD. "
            "Para procesar archivos DWG sin AutoCAD:\n"
            "1. Abre el DWG en cualquier visor CAD gratuito (DWG TrueView, LibreCAD, etc.)\n"
            "2. Exporta/guarda como DXF (Archivo → Guardar como → .dxf)\n"
            "3. Sube el archivo DXF en lugar del DWG\n\n"
            "Si prefieres usar AutoCAD, asegúrate de que esté instalado y ejecutándose."
        ) from exc

    # Abrir el documento
    try:
        document = acad.app.Documents.Open(str(path))
    except Exception as exc:
        logger.error(f"Error al abrir DWG {path.name}: {format_exception(exc)}")
        raise ValueError(
            f"No se pudo abrir el archivo DWG '{path.name}' en AutoCAD. "
            "Puede estar corrupto o ser de una versión muy reciente."
        ) from exc

    results: list[Measurement] = []
    errors = 0
    total_entities = 0

    try:
        for entity in document.ModelSpace:
            total_entities += 1
            try:
                object_name = getattr(entity, "ObjectName", "")
                layer = getattr(entity, "Layer", "0")

                # Saltar entidades de referencia
                if not is_structural(layer):
                    continue
                if object_name in _REFERENCE_OBJECTS:
                    continue

                if object_name.endswith("AcDbLine"):
                    partida = classify_layer(layer).partida
                    start = entity.StartPoint
                    end = entity.EndPoint
                    dx = end[0] - start[0]
                    dy = end[1] - start[1]
                    length = ((dx * dx + dy * dy) ** 0.5) * scale_factor
                    if length > 0:
                        unit = infer_unit(partida, "line")
                        results.append(
                            Measurement("DWG", layer, "line", length, unit,
                                        "Linea AutoCAD", 0.9)
                        )

                elif object_name.endswith("AcDbPolyline") or object_name.endswith("AcDb2dPolyline"):
                    partida = classify_layer(layer).partida
                    length = float(entity.Length) * scale_factor
                    area = float(getattr(entity, "Area", 0) or 0) * (scale_factor**2)
                    has_area = area > 0

                    # Para elementos contables con área, solo crear medición de und
                    if has_area and infer_unit(partida, "closed_polyline") == "und":
                        results.append(
                            Measurement("DWG", layer, "closed_polyline", 1.0, "und",
                                        "Elemento contabilizado", 0.85)
                        )
                    else:
                        if length > 0:
                            poly_unit = infer_unit(partida, "polyline")
                            poly_qty = 1.0 if poly_unit == "und" else length
                            results.append(
                                Measurement("DWG", layer, "polyline", poly_qty, poly_unit,
                                            "Polilinea AutoCAD", 0.85)
                            )
                        if has_area:
                            area_unit = infer_unit(partida, "closed_polyline")
                            area_qty = 1.0 if area_unit == "und" else area
                            results.append(
                                Measurement("DWG", layer, "closed_polyline", area_qty, area_unit,
                                            "Area AutoCAD", 0.85)
                            )

                elif object_name.endswith("AcDbCircle"):
                    partida = classify_layer(layer).partida
                    radius = float(entity.Radius) * scale_factor
                    perimeter = 2 * 3.141592653589793 * radius
                    area = 3.141592653589793 * radius * radius
                    perm_unit = infer_unit(partida, "circle_perimeter")
                    area_unit = infer_unit(partida, "circle_area")
                    perm_qty = 1.0 if perm_unit == "und" else perimeter
                    area_qty = 1.0 if area_unit == "und" else area
                    if perm_unit == "und" or perm_qty > 0:
                        results.append(
                            Measurement("DWG", layer, "circle_perimeter", perm_qty, perm_unit,
                                        "Circulo AutoCAD", 0.8)
                        )
                    if area_unit == "und" or area_qty > 0:
                        results.append(
                            Measurement("DWG", layer, "circle_area", area_qty, area_unit,
                                        "Area de circulo AutoCAD", 0.8)
                        )

            except Exception as exc:
                errors += 1
                if errors <= 5:
                    logger.warning(f"Error procesando entidad {getattr(entity, 'ObjectName', '?')} "
                                   f"en capa {getattr(entity, 'Layer', '?')}: "
                                   f"{format_exception(exc)}")
                continue

    except Exception as exc:
        logger.error(f"Error iterando modelspace de {path.name}: {format_exception(exc)}")
        raise RuntimeError(
            f"Error al leer las entidades del DWG '{path.name}'. "
            "El archivo puede estar dañado."
        ) from exc

    finally:
        try:
            document.Close(False)
        except Exception:
            logger.warning(f"No se pudo cerrar el documento {path.name} en AutoCAD")

    if errors > 0:
        logger.info(f"{errors} entidades no pudieron procesarse en {path.name}")

    if not results:
        logger.warning(f"No se extrajeron mediciones de {path.name} "
                       f"({total_entities} entidades revisadas, {errors} errores)")

    logger.info(f"DWG {path.name}: {len(results)} mediciones extraídas "
                f"({total_entities} entidades, {errors} errores)")
    return results
