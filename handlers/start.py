"""Handlers de /start y /ayuda, y teclado persistente."""

import logging
import re

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, filters

from database.utils import get_manager, verificar_rate_limit
from utils.constants import MENSAJE_AYUDA
from utils.validators import es_chat_privado

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Teclado persistente
# ---------------------------------------------------------------------------

TECLADO_MENU = ReplyKeyboardMarkup(
    [
        ["📋 Mis tareas",  "➕ Nueva tarea"],
        ["💸 Nuevo gasto", "💰 Nuevo ingreso"],
        ["📊 Balance",     "📖 Historial"],
        ["❓ Ayuda"],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# Mapeo por texto sin emojis — newtask/newgasto/newingreso los manejan
# directamente sus ConversationHandlers como entry points
_BOTONES_TEXTO = {
    "mis tareas":  "tareas",
    "balance":     "balance",
    "historial":   "historial",
    "ayuda":       "ayuda",
}


def _extraer_texto(texto: str) -> str:
    """Elimina emojis y caracteres especiales, deja solo letras y espacios."""
    limpio = re.sub(r"[^\w\s]", "", texto, flags=re.UNICODE)
    return " ".join(limpio.split()).lower()


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        await update.message.reply_text("⚠️ Este bot solo funciona en chats privados.")
        return

    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    try:
        get_manager().registrar_usuario(user.id, user.first_name or "Usuario")
    except Exception as e:
        logger.error("Error registrando usuario %s: %s", user.id, e)

    nombre = user.first_name or "amigo"
    await update.message.reply_text(
        f"👋 ¡Hola, {nombre}!\n\n"
        "Soy tu asistente personal de productividad y finanzas.\n"
        "Usa los botones de abajo para navegar rápido. 👇",
        parse_mode="Markdown",
        reply_markup=TECLADO_MENU,
    )


# ---------------------------------------------------------------------------
# /ayuda
# ---------------------------------------------------------------------------

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        await update.message.reply_text("⚠️ Este bot solo funciona en chats privados.")
        return

    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    await update.message.reply_text(
        MENSAJE_AYUDA,
        parse_mode="Markdown",
        reply_markup=TECLADO_MENU,
    )


# ---------------------------------------------------------------------------
# Handler de botones del teclado persistente
# ---------------------------------------------------------------------------

async def menu_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        return

    texto_limpio = _extraer_texto(update.message.text or "")
    comando = _BOTONES_TEXTO.get(texto_limpio)

    if not comando:
        return  # no es un botón del menú

    context.args = []

    if comando == "tareas":
        from handlers.tareas import cmd_tareas
        await cmd_tareas(update, context)

    elif comando == "balance":
        from handlers.consultas import cmd_balance
        await cmd_balance(update, context)

    elif comando == "historial":
        from handlers.consultas import cmd_historial
        await cmd_historial(update, context)

    elif comando == "ayuda":
        await help_handler(update, context)

    elif comando in ("newtask", "newgasto", "newingreso"):
        nombres = {
            "newtask":    "`/newtask`",
            "newgasto":   "`/newgasto`",
            "newingreso": "`/newingreso`",
        }
        await update.message.reply_text(
            f"Escribe {nombres[comando]} para continuar.",
            parse_mode="Markdown",
            reply_markup=TECLADO_MENU,
        )


def build_menu_handler() -> MessageHandler:
    return MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        menu_button_handler,
    )
