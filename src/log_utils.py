"""
Utilidad de logging para la aplicación de metrados.

Centraliza la configuración de logging y provee helpers para
registrar errores, advertencias e información de debug.
"""
from __future__ import annotations

import io
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
_LOG_FILE = _LOG_DIR / "metrados.log"
_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s"
_LOG_LEVEL = logging.INFO

# Buffer en memoria para acceder a los últimos logs desde la UI
_memory_buffer: io.StringIO | None = None


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger configurado con el nombre del módulo."""
    _ensure_log_dir()

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # ya configurado

    logger.setLevel(_LOG_LEVEL)

    # Handler: archivo
    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setLevel(_LOG_LEVEL)
    fh.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(fh)

    # Handler: consola (stderr)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(ch)

    return logger


def get_memory_buffer() -> io.StringIO:
    """Buffer circular en memoria con los últimos mensajes de log.

    Útil para mostrar logs en la UI de Streamlit.
    """
    global _memory_buffer
    if _memory_buffer is None:
        _memory_buffer = io.StringIO()
        mh = logging.StreamHandler(_memory_buffer)
        mh.setLevel(logging.INFO)
        mh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
        # Adjuntar al logger raíz
        root = logging.getLogger()
        root.addHandler(mh)
    return _memory_buffer


def get_recent_logs(n_lines: int = 50) -> str:
    """Devuelve las últimas N líneas del log en memoria."""
    buf = get_memory_buffer()
    lines = buf.getvalue().strip().split("\n")
    return "\n".join(lines[-n_lines:])


def format_exception(exc: BaseException) -> str:
    """Formatea una excepción para logging (traceback resumido)."""
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    # Solo las últimas líneas relevantes
    return "".join(tb[-5:]).strip()


# ---------------------------------------------------------------------------
# Inicialización rápida
# ---------------------------------------------------------------------------
get_logger(__name__).info("Sistema de logging inicializado")
