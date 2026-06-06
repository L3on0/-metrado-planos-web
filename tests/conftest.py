"""
Configuración compartida para pytest.

Agrega el directorio raíz al sys.path para que los tests puedan importar
los módulos de src/ correctamente.
"""
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
