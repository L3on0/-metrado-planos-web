from pathlib import Path

from src.measurements import Measurement


def extract_dwg_measurements(path: Path, scale_factor: float = 1.0) -> list[Measurement]:
    try:
        from pyautocad import Autocad
    except ImportError as exc:
        raise RuntimeError("Instala pyautocad para procesar DWG.") from exc

    acad = Autocad(create_if_not_exists=True)
    document = acad.app.Documents.Open(str(path))
    results: list[Measurement] = []

    try:
        for entity in document.ModelSpace:
            object_name = getattr(entity, "ObjectName", "")
            layer = getattr(entity, "Layer", "0")

            if object_name.endswith("AcDbLine"):
                start = entity.StartPoint
                end = entity.EndPoint
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                length = ((dx * dx + dy * dy) ** 0.5) * scale_factor
                results.append(
                    Measurement("DWG", layer, "line", length, "m", "Linea AutoCAD", 0.9)
                )

            elif object_name.endswith("AcDbPolyline") or object_name.endswith("AcDb2dPolyline"):
                length = float(entity.Length) * scale_factor
                results.append(
                    Measurement("DWG", layer, "polyline", length, "m", "Polilinea AutoCAD", 0.85)
                )
                area = float(getattr(entity, "Area", 0) or 0) * (scale_factor**2)
                if area > 0:
                    results.append(
                        Measurement("DWG", layer, "closed_polyline", area, "m2", "Area AutoCAD", 0.85)
                    )

            elif object_name.endswith("AcDbCircle"):
                radius = float(entity.Radius) * scale_factor
                results.append(
                    Measurement("DWG", layer, "circle_perimeter", 2 * 3.141592653589793 * radius, "m", "Circulo AutoCAD", 0.8)
                )
                results.append(
                    Measurement("DWG", layer, "circle_area", 3.141592653589793 * radius * radius, "m2", "Circulo AutoCAD", 0.8)
                )
    finally:
        document.Close(False)

    return results
