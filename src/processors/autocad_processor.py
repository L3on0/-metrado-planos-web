"""
Procesador de archivos DWG via pyautocad (AutoCAD COM).

Requiere AutoCAD instalado y ejecutándose.
"""
from __future__ import annotations

from pathlib import Path

from src.classification import is_structural
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
                    start = entity.StartPoint
                    end = entity.EndPoint
                    dx = end[0] - start[0]
                    dy = end[1] - start[1]
                    length = ((dx * dx + dy * dy) ** 0.5) * scale_factor
                    if length > 0:
                        results.append(
                            Measurement("DWG", layer, "line", length, "m",
                                        "Linea AutoCAD", 0.9)
                        )

                elif object_name.endswith("AcDbPolyline") or object_name.endswith("AcDb2dPolyline"):
                    length = float(entity.Length) * scale_factor
                    if length > 0:
                        results.append(
                            Measurement("DWG", layer, "polyline", length, "m",
                                        "Polilinea AutoCAD", 0.85)
                        )
                    area = float(getattr(entity, "Area", 0) or 0) * (scale_factor**2)
                    if area > 0:
                        results.append(
                            Measurement("DWG", layer, "closed_polyline", area, "m2",
                                        "Area AutoCAD", 0.85)
                        )

                elif object_name.endswith("AcDbCircle"):
                    radius = float(entity.Radius) * scale_factor
                    perimeter = 2 * 3.141592653589793 * radius
                    area = 3.141592653589793 * radius * radius
                    results.append(
                        Measurement("DWG", layer, "circle_perimeter", perimeter, "m",
                                    "Circulo AutoCAD", 0.8)
                    )
                    results.append(
                        Measurement("DWG", layer, "circle_area", area, "m2",
                                    "Circulo AutoCAD", 0.8)
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
