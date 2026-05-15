"""Handlers de /start y /ayuda."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from database.utils import get_manager, verificar_rate_limit
from utils.constants import MENSAJE_AYUDA
from utils.validators import es_chat_privado

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra al usuario y muestra la bienvenida."""
    if not es_chat_privado(update):
        await update.message.reply_text("⚠️ Este bot solo funciona en chats privados.")
        return

    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos. Espera unos segundos.")
        return

    try:
        get_manager().registrar_usuario(user.id, user.first_name or "Usuario")
    except Exception as e:
        logger.error("Error registrando usuario %s: %s", user.id, e)

    nombre = user.first_name or "amigo"
    await update.message.reply_text(
        f"👋 ¡Hola, {nombre}!\n\n"
        "Soy tu asistente personal de productividad y finanzas.\n\n"
        "Con `/ayuda` ves todos mis comandos disponibles.",
        parse_mode="Markdown",
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el menú de ayuda completo."""
    if not es_chat_privado(update):
        await update.message.reply_text("⚠️ Este bot solo funciona en chats privados.")
        return

    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos. Espera unos segundos.")
        return

    await update.message.reply_text(MENSAJE_AYUDA, parse_mode="Markdown")
