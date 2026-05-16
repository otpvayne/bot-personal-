"""Handlers para gestión de tareas."""

import logging
from datetime import datetime, timedelta

import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database.models import Tarea
from database.utils import get_manager, verificar_rate_limit
from utils.constants import (
    DESCRIPCION_TAREA,
    FECHA_TAREA,
    NOMBRE_TAREA,
    PRIORIDAD_TAREA,
    PRIORIDADES,
)
from utils.formatters import fmt_fecha
from utils.validators import (
    es_chat_privado,
    validar_descripcion_tarea,
    validar_fecha,
    validar_nombre_tarea,
)

logger = logging.getLogger(__name__)
TIMEZONE = "America/Bogota"
_tz = pytz.timezone(TIMEZONE)

# ---------------------------------------------------------------------------
# Teclados
# ---------------------------------------------------------------------------

_TECLADO_PRIORIDAD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔴 Crítica", callback_data="prio_crítica"),
        InlineKeyboardButton("🟠 Alta",    callback_data="prio_alta"),
    ],
    [
        InlineKeyboardButton("🟡 Media",   callback_data="prio_media"),
        InlineKeyboardButton("🟢 Baja",    callback_data="prio_baja"),
    ],
])

_TECLADO_CANCELAR = InlineKeyboardMarkup([
    [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_tarea")]
])


def _teclado_tarea(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Completar", callback_data=f"completar_{task_id}"),
        InlineKeyboardButton("🗑️ Eliminar",  callback_data=f"eliminar_{task_id}"),
    ]])


# ---------------------------------------------------------------------------
# Helper: formatear una tarea con botones
# ---------------------------------------------------------------------------

def _texto_tarea(t: dict) -> str:
    emoji = PRIORIDADES.get(t.get("prioridad", "media"), "⚪")
    prioridad = t.get("prioridad", "media").upper()
    nombre = t.get("nombre", "")
    vence = fmt_fecha(t.get("fecha_vencimiento", ""))
    desc = t.get("descripcion", "")
    lineas = [
        f"{emoji} *[{prioridad}]* {nombre}",
        f"📅 Vence: {vence}",
    ]
    if desc:
        lineas.append(f"📝 {desc}")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# /tarea — creación rápida
# ---------------------------------------------------------------------------

async def cmd_tarea_rapida(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Uso: `/tarea Nombre de la tarea`\nEjemplo: `/tarea Enviar propuesta`",
            parse_mode="Markdown",
        )
        return

    nombre = " ".join(context.args)
    ok, err = validar_nombre_tarea(nombre)
    if not ok:
        await update.message.reply_text(f"❌ {err}")
        return

    hoy = datetime.now(_tz).strftime("%Y-%m-%d")
    tarea = Tarea(nombre=nombre, fecha_vencimiento=hoy, prioridad="media")

    try:
        get_manager().crear_tarea(user.id, tarea)
    except Exception as e:
        logger.error("Error creando tarea: %s", e)
        await update.message.reply_text("❌ Error al guardar la tarea.")
        return

    await update.message.reply_text(
        f"✅ *Tarea creada:*\n\n🟡 {nombre}\n📅 Vence: hoy",
        parse_mode="Markdown",
        reply_markup=_teclado_tarea(tarea.id),
    )


# ---------------------------------------------------------------------------
# /newtask — conversación guiada
# ---------------------------------------------------------------------------

async def cmd_newtask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not es_chat_privado(update):
        return ConversationHandler.END
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text(
        "📝 *Nueva tarea — Paso 1/4*\n\n¿Cuál es el nombre de la tarea?",
        parse_mode="Markdown",
        reply_markup=_TECLADO_CANCELAR,
    )
    return NOMBRE_TAREA


async def recibir_nombre_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nombre = update.message.text.strip()
    ok, err = validar_nombre_tarea(nombre)
    if not ok:
        await update.message.reply_text(f"❌ {err}\nIntenta de nuevo:")
        return NOMBRE_TAREA

    context.user_data["nombre"] = nombre
    await update.message.reply_text(
        "📝 *Nueva tarea — Paso 2/4*\n\n¿Cuándo vence? (YYYY-MM-DD, *hoy* o *mañana*)",
        parse_mode="Markdown",
        reply_markup=_TECLADO_CANCELAR,
    )
    return FECHA_TAREA


async def recibir_fecha_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ok, fecha, err = validar_fecha(update.message.text)
    if not ok:
        await update.message.reply_text(f"❌ {err}\nIntenta de nuevo:")
        return FECHA_TAREA

    context.user_data["fecha"] = fecha.strftime("%Y-%m-%d")
    await update.message.reply_text(
        "📝 *Nueva tarea — Paso 3/4*\n\n¿Cuál es la prioridad?",
        parse_mode="Markdown",
        reply_markup=_TECLADO_PRIORIDAD,
    )
    return PRIORIDAD_TAREA


async def recibir_prioridad_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar_tarea":
        await query.edit_message_text("❌ Creación de tarea cancelada.")
        context.user_data.clear()
        return ConversationHandler.END

    prioridad = query.data.replace("prio_", "")
    context.user_data["prioridad"] = prioridad

    await query.edit_message_text(
        f"📝 *Nueva tarea — Paso 4/4*\n\n"
        f"Prioridad: {PRIORIDADES[prioridad]} {prioridad.capitalize()}\n\n"
        "¿Quieres agregar una descripción? (Escribe o envía *saltar*)",
        parse_mode="Markdown",
    )
    return DESCRIPCION_TAREA


async def recibir_descripcion_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()
    descripcion = "" if texto.lower() in ("saltar", "skip", "-") else texto

    if descripcion:
        ok, descripcion, err = validar_descripcion_tarea(descripcion)
        if not ok:
            await update.message.reply_text(f"❌ {err}\nIntenta de nuevo o escribe *saltar*:")
            return DESCRIPCION_TAREA

    tarea = Tarea(
        nombre=context.user_data["nombre"],
        fecha_vencimiento=context.user_data["fecha"],
        prioridad=context.user_data["prioridad"],
        descripcion=descripcion,
    )

    user = update.effective_user
    try:
        get_manager().crear_tarea(user.id, tarea)
    except Exception as e:
        logger.error("Error creando tarea: %s", e)
        await update.message.reply_text("❌ Error al guardar la tarea.")
        context.user_data.clear()
        return ConversationHandler.END

    await update.message.reply_text(
        f"✅ *¡Tarea creada!*\n\n{_texto_tarea(tarea.to_dict())}",
        parse_mode="Markdown",
        reply_markup=_teclado_tarea(tarea.id),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancelar_tarea_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Creación de tarea cancelada.")
    context.user_data.clear()
    return ConversationHandler.END


async def cmd_cancelar_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Operación cancelada.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /tareas — listar con botones por tarea
# ---------------------------------------------------------------------------

async def cmd_tareas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    filtro = " ".join(context.args).strip().lower() if context.args else ""
    hoy = datetime.now(_tz).date()

    try:
        manager = get_manager()
        if filtro in ("hoy", "today"):
            tareas = manager.listar_tareas_por_fecha(user.id, hoy)
            titulo = "TAREAS PARA HOY"
        elif filtro in ("mañana", "manana", "tomorrow"):
            tareas = manager.listar_tareas_por_fecha(user.id, hoy + timedelta(days=1))
            titulo = "TAREAS PARA MAÑANA"
        elif filtro in ("semana", "week"):
            tareas = manager.listar_tareas_semana(user.id)
            titulo = "TAREAS ESTA SEMANA"
        else:
            tareas = manager.listar_tareas_pendientes(user.id)
            titulo = "TUS TAREAS PENDIENTES"
    except Exception as e:
        logger.error("Error listando tareas: %s", e)
        await update.message.reply_text("❌ Error al obtener las tareas.")
        return

    if not tareas:
        await update.message.reply_text("✅ No tienes tareas pendientes. ¡Estás al día!")
        return

    await update.message.reply_text(
        f"📋 *{titulo}* — {len(tareas)} tarea{'s' if len(tareas) != 1 else ''}",
        parse_mode="Markdown",
    )

    # Cada tarea en su propio mensaje con botones
    for t in tareas:
        await update.message.reply_text(
            _texto_tarea(t),
            parse_mode="Markdown",
            reply_markup=_teclado_tarea(t["id"]),
        )


# ---------------------------------------------------------------------------
# Callbacks de botones ✅ Completar y 🗑️ Eliminar
# ---------------------------------------------------------------------------

async def callback_completar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    task_id = query.data.replace("completar_", "")
    user = update.effective_user

    try:
        exito = get_manager().completar_tarea(user.id, task_id)
    except Exception as e:
        logger.error("Error completando tarea: %s", e)
        await query.edit_message_text("❌ Error al completar la tarea.")
        return

    if exito:
        # Editar el mensaje original quitando los botones
        texto_original = query.message.text or ""
        await query.edit_message_text(
            f"✅ ~~{texto_original}~~\n\n_Completada_ 🎉",
            parse_mode="Markdown",
        )
    else:
        await query.answer("❌ Tarea no encontrada.", show_alert=True)


async def callback_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    task_id = query.data.replace("eliminar_", "")
    user = update.effective_user

    try:
        exito = get_manager().eliminar_tarea(user.id, task_id)
    except Exception as e:
        logger.error("Error eliminando tarea: %s", e)
        await query.edit_message_text("❌ Error al eliminar la tarea.")
        return

    if exito:
        await query.edit_message_text("🗑️ _Tarea eliminada._", parse_mode="Markdown")
    else:
        await query.answer("❌ Tarea no encontrada.", show_alert=True)


# ---------------------------------------------------------------------------
# ConversationHandler de /newtask + handlers de botones
# ---------------------------------------------------------------------------

def build_newtask_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("newtask", cmd_newtask),
            MessageHandler(filters.Regex(r"(?i)nueva\s*tarea"), cmd_newtask),
        ],
        states={
            NOMBRE_TAREA:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre_tarea)],
            FECHA_TAREA:     [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_fecha_tarea)],
            PRIORIDAD_TAREA: [CallbackQueryHandler(recibir_prioridad_callback, pattern="^(prio_|cancelar_tarea)")],
            DESCRIPCION_TAREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion_tarea)],
        },
        fallbacks=[
            CommandHandler("cancelar", cmd_cancelar_tarea),
            CallbackQueryHandler(cancelar_tarea_callback, pattern="^cancelar_tarea$"),
        ],
        allow_reentry=True,
    )


def build_tarea_action_handlers() -> list:
    """Retorna los CallbackQueryHandlers para completar y eliminar tareas."""
    return [
        CallbackQueryHandler(callback_completar, pattern="^completar_"),
        CallbackQueryHandler(callback_eliminar,  pattern="^eliminar_"),
    ]
