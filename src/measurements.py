from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.classification import (
    CAT_REFERENCE,
    CAT_STRUCTURAL,
    classify_measurement,
    filter_structural,
    is_structural,
)


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


def classify(measurement: Measurement) -> tuple[str, str, str]:
    """Clasifica un Measurement en (partida, descripcion, categoria).

    Reemplaza a la antigua ``infer_partida()``. Usa el módulo de
    clasificación inteligente por capa.
    """
    partida, descripcion, categoria = classify_measurement(
        measurement.layer,
        measurement.element_type,
        measurement.description,
    )
    return partida, descripcion, categoria


def build_metrado(measurements: Iterable[Measurement],
                  include_reference: bool = False) -> list[MetradoItem]:
    """Agrupa mediciones por partida y devuelve items de metrado.

    Por defecto filta elementos de referencia (cotas, ejes, texto…).
    Pasar ``include_reference=True`` para incluirlos.
    """
    grouped: dict[tuple[str, str, str], list[Measurement]] = {}

    for measurement in measurements:
        partida, descripcion, categoria = classify(measurement)
        if not include_reference and categoria == CAT_REFERENCE:
            continue
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


def measurements_to_rows(measurements: Iterable[Measurement],
                         include_reference: bool = False) -> list[dict]:
    """Convierte mediciones a filas planas para mostrar en tabla.

    Por defecto excluye elementos de referencia.
    """
    rows = []
    for m in measurements:
        _partida, _desc, categoria = classify(m)
        if not include_reference and categoria == CAT_REFERENCE:
            continue
        rows.append({
            "fuente": m.source,
            "capa": m.layer,
            "tipo": m.element_type,
            "cantidad": round(m.quantity, 3),
            "unidad": m.unit,
            "descripcion": m.description,
            "confianza": round(m.confidence, 2),
            "partida": _partida,
        })
    return rows


# Mantener compatibilidad hacia atrás
infer_partida = classify
