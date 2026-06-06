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
                  include_reference: bool = False,
                  apply_noise_filter: bool = True) -> list[MetradoItem]:
    """Agrupa mediciones por partida y devuelve items de metrado.

    Args:
        measurements: Mediciones a agrupar.
        include_reference: Si True, incluye elementos de referencia.
        apply_noise_filter: Si True, elimina mediciones demasiado pequeñas y duplicadas.

    Por defecto filta elementos de referencia (cotas, ejes, texto…).
    Pasar ``include_reference=True`` para incluirlos.
    """
    all_m = list(measurements)
    if apply_noise_filter:
        all_m = filter_noise(all_m)

    grouped: dict[tuple[str, str, str], list[Measurement]] = {}

    for measurement in all_m:
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
                         include_reference: bool = False,
                         apply_noise_filter: bool = True) -> list[dict]:
    """Convierte mediciones a filas planas para mostrar en tabla.

    Por defecto excluye elementos de referencia.
    """
    all_m = list(measurements)
    if apply_noise_filter:
        all_m = filter_noise(all_m)

    rows = []
    for m in all_m:
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


# ---------------------------------------------------------------------------
# Filtros de ruido
# ---------------------------------------------------------------------------

MIN_LENGTH_M = 0.10    # metros — ignorar líneas más cortas
MIN_AREA_M2 = 0.01     # metros² — ignorar áreas más pequeñas
_LENGTH_TOLERANCE = 0.05  # tolerancia 5% para detección de duplicados


def should_filter_by_size(quantity: float, unit: str) -> bool:
    """Determina si una medición debe filtrarse por ser demasiado pequeña.

    Args:
        quantity: Valor numérico de la medición.
        unit: Unidad ('m', 'm2', 'und', etc.).

    Returns:
        True si la medición es demasiado pequeña para ser significativa.
    """
    if unit == "m" and quantity < MIN_LENGTH_M:
        return True
    if unit == "m2" and quantity < MIN_AREA_M2:
        return True
    return False


def filter_noise(measurements: list[Measurement]) -> list[Measurement]:
    """Filtra mediciones ruidosas: demasiado pequeñas o duplicadas.

    Args:
        measurements: Lista de mediciones.

    Returns:
        Lista filtrada.
    """
    # 1. Filtrar por tamaño
    filtered = [m for m in measurements if not should_filter_by_size(m.quantity, m.unit)]

    # 2. Detectar duplicados (misma capa + tipo + longitud similar)
    #    No deduplicar elementos contados por unidad (und) — cada uno es único
    seen: set[tuple] = set()
    deduped: list[Measurement] = []
    for m in filtered:
        if m.unit == "und":
            deduped.append(m)
            continue
        rounded = round(m.quantity / _LENGTH_TOLERANCE) * _LENGTH_TOLERANCE
        key = (m.layer, m.element_type, m.source, rounded)
        if key not in seen:
            seen.add(key)
            deduped.append(m)

    return deduped
