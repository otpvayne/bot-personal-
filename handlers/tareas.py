"""Handlers para gestión de tareas."""

import logging
from datetime import datetime

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
    PRIORIDADES_LISTA,
)
from utils.formatters import formatear_lista_tareas
from utils.validators import (
    es_chat_privado,
    validar_descripcion_tarea,
    validar_fecha,
    validar_nombre_tarea,
    validar_prioridad,
)

logger = logging.getLogger(__name__)
TIMEZONE = "America/Bogota"
_tz = pytz.timezone(TIMEZONE)

# ---------------------------------------------------------------------------
# Teclado inline de prioridades
# ---------------------------------------------------------------------------

_TECLADO_PRIORIDAD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔴 Crítica", callback_data="prio_crítica"),
        InlineKeyboardButton("🟠 Alta", callback_data="prio_alta"),
    ],
    [
        InlineKeyboardButton("🟡 Media", callback_data="prio_media"),
        InlineKeyboardButton("🟢 Baja", callback_data="prio_baja"),
    ],
])

_TECLADO_CANCELAR = InlineKeyboardMarkup([
    [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_tarea")]
])


# ---------------------------------------------------------------------------
# /tarea — creación rápida
# ---------------------------------------------------------------------------

async def cmd_tarea_rapida(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Crea una tarea rápida con la fecha de hoy y prioridad media."""
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos. Espera unos segundos.")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ Uso: `/tarea Nombre de la tarea`\n"
            "Ejemplo: `/tarea Enviar propuesta`",
            parse_mode="Markdown",
        )
        return

    nombre = " ".join(args)
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
        await update.message.reply_text("❌ Error al guardar la tarea. Intenta de nuevo.")
        return

    emoji = PRIORIDADES["media"]
    await update.message.reply_text(
        f"✅ *Tarea creada:*\n\n"
        f"{emoji} {nombre}\n"
        f"📅 Vence: hoy\n"
        f"🆔 ID: `{tarea.id}`",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# /newtask — conversación guiada
# ---------------------------------------------------------------------------

async def cmd_newtask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el flujo de creación de tarea detallada."""
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
        "📝 *Nueva tarea — Paso 2/4*\n\n"
        "¿Cuándo vence? (YYYY-MM-DD, *hoy* o *mañana*)",
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
    """Procesa la prioridad seleccionada por botón."""
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

    emoji = PRIORIDADES[tarea.prioridad]
    desc_txt = f"\n📄 {tarea.descripcion}" if tarea.descripcion else ""
    await update.message.reply_text(
        f"✅ *¡Tarea creada!*\n\n"
        f"{emoji} *{tarea.nombre}*\n"
        f"📅 Vence: {tarea.fecha_vencimiento}\n"
        f"🎯 Prioridad: {tarea.prioridad.capitalize()}"
        f"{desc_txt}\n"
        f"🆔 ID: `{tarea.id}`",
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancelar_tarea_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "cancelar_tarea":
        await query.edit_message_text("❌ Creación de tarea cancelada.")
        context.user_data.clear()
    return ConversationHandler.END


async def cmd_cancelar_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación con /cancelar."""
    context.user_data.clear()
    await update.message.reply_text("❌ Operación cancelada.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /tareas — listar
# ---------------------------------------------------------------------------

async def cmd_tareas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista tareas pendientes con filtros opcionales."""
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
            from datetime import timedelta
            manana = hoy + timedelta(days=1)
            tareas = manager.listar_tareas_por_fecha(user.id, manana)
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

    mensaje = formatear_lista_tareas(tareas, titulo)
    await update.message.reply_text(mensaje, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /completar — marcar tarea como hecha
# ---------------------------------------------------------------------------

async def cmd_completar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Uso: `/completar ID_DE_TAREA`\n"
            "Usa `/tareas` para ver los IDs.",
            parse_mode="Markdown",
        )
        return

    task_id = context.args[0].strip()
    try:
        exito = get_manager().completar_tarea(user.id, task_id)
    except Exception as e:
        logger.error("Error completando tarea: %s", e)
        await update.message.reply_text("❌ Error al completar la tarea.")
        return

    if exito:
        await update.message.reply_text(
            f"✅ Tarea `{task_id}` marcada como completada. ¡Buen trabajo!",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"❌ No encontré ninguna tarea con ID `{task_id}`.",
            parse_mode="Markdown",
        )


# ---------------------------------------------------------------------------
# /eliminar — eliminar tarea
# ---------------------------------------------------------------------------

async def cmd_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Uso: `/eliminar ID_DE_TAREA`\n"
            "Usa `/tareas` para ver los IDs.",
            parse_mode="Markdown",
        )
        return

    task_id = context.args[0].strip()
    try:
        exito = get_manager().eliminar_tarea(user.id, task_id)
    except Exception as e:
        logger.error("Error eliminando tarea: %s", e)
        await update.message.reply_text("❌ Error al eliminar la tarea.")
        return

    if exito:
        await update.message.reply_text(
            f"🗑️ Tarea `{task_id}` eliminada.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"❌ No encontré ninguna tarea con ID `{task_id}`.",
            parse_mode="Markdown",
        )


# ---------------------------------------------------------------------------
# ConversationHandler de /newtask
# ---------------------------------------------------------------------------

def build_newtask_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("newtask", cmd_newtask)],
        states={
            NOMBRE_TAREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre_tarea)],
            FECHA_TAREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_fecha_tarea)],
            PRIORIDAD_TAREA: [
                CallbackQueryHandler(recibir_prioridad_callback, pattern="^(prio_|cancelar_tarea)"),
            ],
            DESCRIPCION_TAREA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion_tarea)
            ],
        },
        fallbacks=[
            CommandHandler("cancelar", cmd_cancelar_tarea),
            CallbackQueryHandler(cancelar_tarea_callback, pattern="^cancelar_tarea$"),
        ],
        allow_reentry=True,
    )
