from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Measurement:
    source: str
    layer: str
    element_type: str
    quantity: float
    unit: str
    description: str
    confidence: float = 0.7


@dataclass(frozen=True)
class MetradoItem:
    partida: str
    descripcion: str
    unidad: str
    cantidad: float
    fuente: str
    confianza: float

    def as_dict(self) -> dict:
        return {
            "partida": self.partida,
            "descripcion": self.descripcion,
            "unidad": self.unidad,
            "cantidad": round(self.cantidad, 3),
            "fuente": self.fuente,
            "confianza": round(self.confianza, 2),
        }


def infer_partida(measurement: Measurement) -> tuple[str, str]:
    layer = measurement.layer.lower()
    text = measurement.description.lower()

    if "muro" in layer or "wall" in layer or "muro" in text:
        return "ARQ-01", "Muros detectados"
    if "piso" in layer or "floor" in layer or "area" in measurement.unit:
        return "ARQ-02", "Areas de piso o superficie"
    if "zocalo" in layer or "baseboard" in layer:
        return "ARQ-03", "Zocalos detectados"
    if "cota" in layer or "dimension" in layer or measurement.element_type == "dimension_text":
        return "REF-01", "Cotas de referencia"
    return "GEN-01", "Elementos lineales generales"


def build_metrado(measurements: Iterable[Measurement]) -> list[MetradoItem]:
    grouped: dict[tuple[str, str, str], list[Measurement]] = {}

    for measurement in measurements:
        partida, descripcion = infer_partida(measurement)
        key = (partida, descripcion, measurement.unit)
        grouped.setdefault(key, []).append(measurement)

    items: list[MetradoItem] = []
    for (partida, descripcion, unit), group in grouped.items():
        quantity = sum(item.quantity for item in group)
        confidence = sum(item.confidence for item in group) / len(group)
        fuente = ", ".join(sorted({item.source for item in group}))
        items.append(
            MetradoItem(
                partida=partida,
                descripcion=descripcion,
                unidad=unit,
                cantidad=quantity,
                fuente=fuente,
                confianza=confidence,
            )
        )

    return sorted(items, key=lambda item: item.partida)


def measurements_to_rows(measurements: Iterable[Measurement]) -> list[dict]:
    return [
        {
            "fuente": item.source,
            "capa": item.layer,
            "tipo": item.element_type,
            "cantidad": round(item.quantity, 3),
            "unidad": item.unit,
            "descripcion": item.description,
            "confianza": round(item.confidence, 2),
        }
        for item in measurements
    ]
