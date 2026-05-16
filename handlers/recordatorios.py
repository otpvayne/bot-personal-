"""Recordatorio diario de tareas a las 7 AM hora Colombia."""

import logging
from datetime import datetime

import pytz
from telegram.ext import ContextTypes

from database.utils import get_manager
from utils.formatters import emoji_prioridad, fmt_fecha

logger = logging.getLogger(__name__)
TIMEZONE = "America/Bogota"
_tz = pytz.timezone(TIMEZONE)


async def recordatorio_diario(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Se ejecuta cada día a las 7 AM. Envía tareas del día a cada usuario."""
    hoy = datetime.now(_tz).date()
    manager = get_manager()

    try:
        user_ids = manager.obtener_todos_usuarios()
    except Exception as e:
        logger.error("Error obteniendo usuarios para recordatorio: %s", e)
        return

    for user_id in user_ids:
        try:
            tareas = manager.listar_tareas_por_fecha(user_id, hoy)
            if not tareas:
                continue  # sin tareas hoy, no molestar

            lineas = ["☀️ *Buenos días\\! Tus tareas para hoy:*\n"]
            for t in tareas:
                emoji = emoji_prioridad(t.get("prioridad", "media"))
                nombre = t.get("nombre", "")
                lineas.append(f"{emoji} {nombre}")

            lineas.append(f"\nTotal: {len(tareas)} tarea{'s' if len(tareas) != 1 else ''}")
            lineas.append("Usa /tareas para ver los detalles.")

            await context.bot.send_message(
                chat_id=user_id,
                text="\n".join(lineas),
                parse_mode="Markdown",
            )
            logger.info("Recordatorio enviado a user_id=%s (%d tareas)", user_id, len(tareas))

        except Exception as e:
            logger.error("Error enviando recordatorio a %s: %s", user_id, e)
