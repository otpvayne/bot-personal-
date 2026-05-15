"""Punto de entrada del bot de Telegram."""

import logging

from telegram.ext import Application, CommandHandler

import config
from handlers.consultas import (
    cmd_balance,
    cmd_categoria,
    cmd_historial,
    cmd_mes,
    cmd_reporte,
)
from handlers.finanzas import (
    build_newgasto_conversation,
    build_newingreso_conversation,
    cmd_gasto_rapido,
    cmd_ingreso_rapido,
)
from handlers.start import help_handler, start_handler
from handlers.tareas import (
    build_newtask_conversation,
    cmd_completar,
    cmd_eliminar,
    cmd_tarea_rapida,
    cmd_tareas,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # --- Información ---
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("ayuda", help_handler))

    # --- Tareas ---
    app.add_handler(build_newtask_conversation())
    app.add_handler(CommandHandler("tarea", cmd_tarea_rapida))
    app.add_handler(CommandHandler("tareas", cmd_tareas))
    app.add_handler(CommandHandler("completar", cmd_completar))
    app.add_handler(CommandHandler("eliminar", cmd_eliminar))

    # --- Finanzas rápidas ---
    app.add_handler(CommandHandler("gasto", cmd_gasto_rapido))
    app.add_handler(CommandHandler("ingreso", cmd_ingreso_rapido))

    # --- Finanzas conversacionales ---
    app.add_handler(build_newgasto_conversation())
    app.add_handler(build_newingreso_conversation())

    # --- Consultas ---
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("historial", cmd_historial))
    app.add_handler(CommandHandler("mes", cmd_mes))
    app.add_handler(CommandHandler("categoria", cmd_categoria))
    app.add_handler(CommandHandler("reporte", cmd_reporte))

    logger.info("Bot iniciado — entorno=%s", config.ENVIRONMENT)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
