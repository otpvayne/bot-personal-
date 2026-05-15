"""Configuración del bot leída desde variables de entorno."""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Obligatorias
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]

FIREBASE_DB_URL: str = os.environ["FIREBASE_DB_URL"]

# ---------------------------------------------------------------------------
# Credenciales de Firebase (una de las dos debe estar presente)
# ---------------------------------------------------------------------------

# Opción A: ruta al archivo JSON descargado de la consola de Firebase
FIREBASE_CREDENTIALS_PATH: str = os.getenv(
    "FIREBASE_CREDENTIALS_PATH", "./serviceAccountKey.json"
)

# Opción B: contenido del JSON como string (ideal para Railway sin archivos locales)
FIREBASE_CREDENTIALS_JSON: str | None = os.getenv("FIREBASE_CREDENTIALS_JSON")

# ---------------------------------------------------------------------------
# Opcionales
# ---------------------------------------------------------------------------

ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

IS_DEVELOPMENT: bool = ENVIRONMENT.lower() == "development"
