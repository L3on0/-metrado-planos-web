import os
from pathlib import Path

os.environ.setdefault("EZDXF_CACHE_DIR", str(Path(__file__).resolve().parents[2] / "data" / "ezdxf_cache"))
import ezdxf

from src.measurements import Measurement


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


def extract_dxf_measurements(path: Path, scale_factor: float = 1.0) -> list[Measurement]:
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    results: list[Measurement] = []

    for entity in msp:
        dxftype = entity.dxftype()
        layer = getattr(entity.dxf, "layer", "0")

        if dxftype == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            dx = end.x - start.x
            dy = end.y - start.y
            length = ((dx * dx + dy * dy) ** 0.5) * scale_factor
            results.append(
                Measurement("DXF", layer, "line", length, "m", "Linea detectada", 0.9)
            )

        elif dxftype in {"LWPOLYLINE", "POLYLINE"}:
            if dxftype == "LWPOLYLINE":
                points = [(point[0], point[1]) for point in entity.get_points()]
                is_closed = entity.closed
            else:
                points = [(vertex.dxf.location.x, vertex.dxf.location.y) for vertex in entity.vertices]
                is_closed = entity.is_closed

            length = _polyline_length(points)
            if is_closed:
                length += _polyline_length([points[-1], points[0]]) if len(points) > 1 else 0.0
                area = _polygon_area(points) * (scale_factor**2)
                results.append(
                    Measurement("DXF", layer, "closed_polyline", area, "m2", "Polilinea cerrada", 0.85)
                )
            results.append(
                Measurement("DXF", layer, "polyline", length * scale_factor, "m", "Polilinea detectada", 0.85)
            )

        elif dxftype == "CIRCLE":
            radius = entity.dxf.radius * scale_factor
            perimeter = 2 * 3.141592653589793 * radius
            area = 3.141592653589793 * radius * radius
            results.append(
                Measurement("DXF", layer, "circle_perimeter", perimeter, "m", "Perimetro de circulo", 0.8)
            )
            results.append(
                Measurement("DXF", layer, "circle_area", area, "m2", "Area de circulo", 0.8)
            )

    return results
