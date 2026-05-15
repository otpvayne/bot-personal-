"""Utilidades de base de datos: rate limiting y singleton del manager."""

import time
from collections import defaultdict
from typing import Dict, List

from database.firebase_manager import FirebaseManager

# ---------------------------------------------------------------------------
# Singleton de FirebaseManager
# ---------------------------------------------------------------------------

_manager_instance: "FirebaseManager | None" = None


def get_manager() -> FirebaseManager:
    """Retorna la instancia compartida de FirebaseManager."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = FirebaseManager()
    return _manager_instance


# ---------------------------------------------------------------------------
# Rate limiting simple en memoria
# ---------------------------------------------------------------------------

# {user_id: [timestamps de comandos recientes]}
_rate_buckets: Dict[int, List[float]] = defaultdict(list)

LIMITE = 10      # máximo comandos
VENTANA = 10.0   # segundos


def verificar_rate_limit(user_id: int) -> bool:
    """
    Retorna True si el usuario puede ejecutar el comando.
    Retorna False si superó el límite.
    """
    ahora = time.monotonic()
    bucket = _rate_buckets[user_id]
    # Remover entradas fuera de la ventana
    _rate_buckets[user_id] = [t for t in bucket if ahora - t < VENTANA]
    if len(_rate_buckets[user_id]) >= LIMITE:
        return False
    _rate_buckets[user_id].append(ahora)
    return True
