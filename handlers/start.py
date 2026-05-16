"""Handlers de /start y /ayuda, y teclado persistente."""

import logging

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
    resize_keyboard=True,       # se adapta al tamaño del celular
    is_persistent=True,         # queda fijo aunque se envíen otros mensajes
)

# Mapeo botón → comando interno
_BOTONES = {
    "📋 mis tareas":   "tareas",
    "➕ nueva tarea":  "newtask",
    "💸 nuevo gasto":  "newgasto",
    "💰 nuevo ingreso":"newingreso",
    "📊 balance":      "balance",
    "📖 historial":    "historial",
    "❓ ayuda":        "ayuda",
}


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
    """Intercepta los textos del teclado y los redirige al comando correcto."""
    if not es_chat_privado(update):
        return

    texto = update.message.text.strip().lower()
    comando = _BOTONES.get(texto)

    if not comando:
        return  # no es un botón del menú, ignorar

    # Simular que el usuario escribió el comando
    context.args = []
    update.message.text = f"/{comando}"

    # Importar y llamar el handler correspondiente
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
        # Los flujos de conversación no se pueden llamar directamente,
        # le decimos al usuario que escriba el comando
        nombres = {
            "newtask":    "/newtask — crear tarea con detalles",
            "newgasto":   "/newgasto — registrar gasto con categoría",
            "newingreso": "/newingreso — registrar ingreso con categoría",
        }
        await update.message.reply_text(
            f"Escribe {nombres[comando]}",
            reply_markup=TECLADO_MENU,
        )


def build_menu_handler() -> MessageHandler:
    """Retorna el handler que escucha los botones del teclado persistente."""
    botones_pattern = "|".join(
        b.replace("+", r"\+") for b in [
            "📋 Mis tareas", "➕ Nueva tarea", "💸 Nuevo gasto",
            "💰 Nuevo ingreso", "📊 Balance", "📖 Historial", "❓ Ayuda",
        ]
    )
    return MessageHandler(
        filters.TEXT & filters.Regex(f"^({botones_pattern})$") & ~filters.COMMAND,
        menu_button_handler,
    )
