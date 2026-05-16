"""Handlers para registro de gastos e ingresos."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database.models import Transaccion
from database.utils import get_manager, verificar_rate_limit
from utils.constants import (
    CATEGORIAS_GASTO,
    CATEGORIAS_INGRESO,
    CATEGORIA_GASTO,
    CATEGORIA_INGRESO,
    DESCRIPCION_GASTO,
    DESCRIPCION_INGRESO,
    MONTO_GASTO,
    MONTO_INGRESO,
)
from utils.formatters import fmt_monto
from utils.validators import (
    es_chat_privado,
    validar_categoria_gasto,
    validar_categoria_ingreso,
    validar_descripcion_finanza,
    validar_monto,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Teclados inline de categorías
# ---------------------------------------------------------------------------

def _teclado_categorias_gasto() -> InlineKeyboardMarkup:
    botones = []
    cats = list(CATEGORIAS_GASTO.items())
    for i in range(0, len(cats), 2):
        fila = []
        for cat, emoji in cats[i:i+2]:
            fila.append(InlineKeyboardButton(f"{emoji} {cat}", callback_data=f"cat_gasto_{cat}"))
        botones.append(fila)
    botones.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_finanza")])
    return InlineKeyboardMarkup(botones)


def _teclado_categorias_ingreso() -> InlineKeyboardMarkup:
    botones = []
    cats = list(CATEGORIAS_INGRESO.items())
    for i in range(0, len(cats), 2):
        fila = []
        for cat, emoji in cats[i:i+2]:
            fila.append(InlineKeyboardButton(f"{emoji} {cat}", callback_data=f"cat_ingreso_{cat}"))
        botones.append(fila)
    botones.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_finanza")])
    return InlineKeyboardMarkup(botones)


_CANCELAR_BTN = InlineKeyboardMarkup([
    [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_finanza")]
])


# ---------------------------------------------------------------------------
# /gasto — registro rápido
# ---------------------------------------------------------------------------

async def cmd_gasto_rapido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra un gasto rápido: /gasto 20000 descripción opcional."""
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Uso: `/gasto MONTO descripción`\n"
            "Ejemplo: `/gasto 20000 almuerzo`",
            parse_mode="Markdown",
        )
        return

    ok, monto, err = validar_monto(context.args[0])
    if not ok:
        await update.message.reply_text(f"❌ {err}")
        return

    descripcion = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    tx = Transaccion(tipo="gasto", monto=monto, categoria="Otros", descripcion=descripcion)

    try:
        get_manager().crear_transaccion(user.id, tx)
    except Exception as e:
        logger.error("Error registrando gasto: %s", e)
        await update.message.reply_text("❌ Error al registrar el gasto.")
        return

    desc_txt = f"\n📝 {descripcion}" if descripcion else ""
    await update.message.reply_text(
        f"❌ *Gasto registrado:*\n\n"
        f"💸 {fmt_monto(monto)} — Otros"
        f"{desc_txt}\n"
        f"🆔 ID: `{tx.id}`",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# /ingreso — registro rápido
# ---------------------------------------------------------------------------

async def cmd_ingreso_rapido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra un ingreso rápido: /ingreso 300000 descripción opcional."""
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Uso: `/ingreso MONTO descripción`\n"
            "Ejemplo: `/ingreso 300000 proyecto web`",
            parse_mode="Markdown",
        )
        return

    ok, monto, err = validar_monto(context.args[0])
    if not ok:
        await update.message.reply_text(f"❌ {err}")
        return

    descripcion = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    tx = Transaccion(tipo="ingreso", monto=monto, categoria="Otros", descripcion=descripcion)

    try:
        get_manager().crear_transaccion(user.id, tx)
    except Exception as e:
        logger.error("Error registrando ingreso: %s", e)
        await update.message.reply_text("❌ Error al registrar el ingreso.")
        return

    desc_txt = f"\n📝 {descripcion}" if descripcion else ""
    await update.message.reply_text(
        f"✅ *Ingreso registrado:*\n\n"
        f"💰 {fmt_monto(monto)} — Otros"
        f"{desc_txt}\n"
        f"🆔 ID: `{tx.id}`",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# /newgasto — conversación guiada
# ---------------------------------------------------------------------------

async def cmd_newgasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not es_chat_privado(update):
        return ConversationHandler.END
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["tipo"] = "gasto"
    await update.message.reply_text(
        "💸 *Nuevo gasto — Paso 1/3*\n\n¿Cuánto gastaste?",
        parse_mode="Markdown",
        reply_markup=_CANCELAR_BTN,
    )
    return MONTO_GASTO


async def recibir_monto_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ok, monto, err = validar_monto(update.message.text)
    if not ok:
        await update.message.reply_text(f"❌ {err}\nIntenta de nuevo:")
        return MONTO_GASTO

    context.user_data["monto"] = monto
    await update.message.reply_text(
        f"💸 *Nuevo gasto — Paso 2/3*\n\n"
        f"Monto: {fmt_monto(monto)}\n\n"
        "¿En qué categoría?",
        parse_mode="Markdown",
        reply_markup=_teclado_categorias_gasto(),
    )
    return CATEGORIA_GASTO


async def recibir_categoria_gasto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar_finanza":
        await query.edit_message_text("❌ Registro cancelado.")
        context.user_data.clear()
        return ConversationHandler.END

    categoria = query.data.replace("cat_gasto_", "")
    context.user_data["categoria"] = categoria
    monto = context.user_data["monto"]

    await query.edit_message_text(
        f"💸 *Nuevo gasto — Paso 3/3*\n\n"
        f"Monto: {fmt_monto(monto)}\n"
        f"Categoría: {CATEGORIAS_GASTO.get(categoria, '📌')} {categoria}\n\n"
        "¿Alguna descripción? (Escribe o envía *saltar*)",
        parse_mode="Markdown",
    )
    return DESCRIPCION_GASTO


async def recibir_descripcion_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()
    descripcion = "" if texto.lower() in ("saltar", "skip", "-") else texto

    if descripcion:
        ok, descripcion, err = validar_descripcion_finanza(descripcion)
        if not ok:
            await update.message.reply_text(f"❌ {err}\nIntenta de nuevo o escribe *saltar*:")
            return DESCRIPCION_GASTO

    tx = Transaccion(
        tipo="gasto",
        monto=context.user_data["monto"],
        categoria=context.user_data["categoria"],
        descripcion=descripcion,
    )

    user = update.effective_user
    try:
        get_manager().crear_transaccion(user.id, tx)
    except Exception as e:
        logger.error("Error registrando gasto: %s", e)
        await update.message.reply_text("❌ Error al guardar el gasto.")
        context.user_data.clear()
        return ConversationHandler.END

    emoji = CATEGORIAS_GASTO.get(tx.categoria, "📌")
    desc_txt = f"\n📝 {tx.descripcion}" if tx.descripcion else ""
    await update.message.reply_text(
        f"✅ *¡Gasto registrado!*\n\n"
        f"💸 {fmt_monto(tx.monto)}\n"
        f"{emoji} Categoría: {tx.categoria}"
        f"{desc_txt}\n"
        f"🆔 ID: `{tx.id}`",
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /newingreso — conversación guiada
# ---------------------------------------------------------------------------

async def cmd_newingreso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not es_chat_privado(update):
        return ConversationHandler.END
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["tipo"] = "ingreso"
    await update.message.reply_text(
        "💰 *Nuevo ingreso — Paso 1/3*\n\n¿Cuánto recibiste?",
        parse_mode="Markdown",
        reply_markup=_CANCELAR_BTN,
    )
    return MONTO_INGRESO


async def recibir_monto_ingreso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ok, monto, err = validar_monto(update.message.text)
    if not ok:
        await update.message.reply_text(f"❌ {err}\nIntenta de nuevo:")
        return MONTO_INGRESO

    context.user_data["monto"] = monto
    await update.message.reply_text(
        f"💰 *Nuevo ingreso — Paso 2/3*\n\n"
        f"Monto: {fmt_monto(monto)}\n\n"
        "¿En qué categoría?",
        parse_mode="Markdown",
        reply_markup=_teclado_categorias_ingreso(),
    )
    return CATEGORIA_INGRESO


async def recibir_categoria_ingreso_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "cancelar_finanza":
        await query.edit_message_text("❌ Registro cancelado.")
        context.user_data.clear()
        return ConversationHandler.END

    categoria = query.data.replace("cat_ingreso_", "")
    context.user_data["categoria"] = categoria
    monto = context.user_data["monto"]

    await query.edit_message_text(
        f"💰 *Nuevo ingreso — Paso 3/3*\n\n"
        f"Monto: {fmt_monto(monto)}\n"
        f"Categoría: {CATEGORIAS_INGRESO.get(categoria, '📌')} {categoria}\n\n"
        "¿Alguna descripción? (Escribe o envía *saltar*)",
        parse_mode="Markdown",
    )
    return DESCRIPCION_INGRESO


async def recibir_descripcion_ingreso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()
    descripcion = "" if texto.lower() in ("saltar", "skip", "-") else texto

    if descripcion:
        ok, descripcion, err = validar_descripcion_finanza(descripcion)
        if not ok:
            await update.message.reply_text(f"❌ {err}\nIntenta de nuevo o escribe *saltar*:")
            return DESCRIPCION_INGRESO

    tx = Transaccion(
        tipo="ingreso",
        monto=context.user_data["monto"],
        categoria=context.user_data["categoria"],
        descripcion=descripcion,
    )

    user = update.effective_user
    try:
        get_manager().crear_transaccion(user.id, tx)
    except Exception as e:
        logger.error("Error registrando ingreso: %s", e)
        await update.message.reply_text("❌ Error al guardar el ingreso.")
        context.user_data.clear()
        return ConversationHandler.END

    emoji = CATEGORIAS_INGRESO.get(tx.categoria, "📌")
    desc_txt = f"\n📝 {tx.descripcion}" if tx.descripcion else ""
    await update.message.reply_text(
        f"✅ *¡Ingreso registrado!*\n\n"
        f"💰 {fmt_monto(tx.monto)}\n"
        f"{emoji} Categoría: {tx.categoria}"
        f"{desc_txt}\n"
        f"🆔 ID: `{tx.id}`",
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Cancelar finanza (fallback genérico)
# ---------------------------------------------------------------------------

async def cmd_cancelar_finanza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Operación cancelada.")
    return ConversationHandler.END


async def cancelar_finanza_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Operación cancelada.")
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# ConversationHandlers
# ---------------------------------------------------------------------------

def build_newgasto_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("newgasto", cmd_newgasto),
            MessageHandler(filters.Regex(r"(?i)nuevo\s*gasto"), cmd_newgasto),
        ],
        states={
            MONTO_GASTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto_gasto)],
            CATEGORIA_GASTO: [
                CallbackQueryHandler(recibir_categoria_gasto_callback, pattern="^(cat_gasto_|cancelar_finanza)")
            ],
            DESCRIPCION_GASTO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion_gasto)
            ],
        },
        fallbacks=[
            CommandHandler("cancelar", cmd_cancelar_finanza),
            CallbackQueryHandler(cancelar_finanza_callback, pattern="^cancelar_finanza$"),
        ],
        allow_reentry=True,
    )


def build_newingreso_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("newingreso", cmd_newingreso),
            MessageHandler(filters.Regex(r"(?i)nuevo\s*ingreso"), cmd_newingreso),
        ],
        states={
            MONTO_INGRESO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto_ingreso)],
            CATEGORIA_INGRESO: [
                CallbackQueryHandler(recibir_categoria_ingreso_callback, pattern="^(cat_ingreso_|cancelar_finanza)")
            ],
            DESCRIPCION_INGRESO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion_ingreso)
            ],
        },
        fallbacks=[
            CommandHandler("cancelar", cmd_cancelar_finanza),
            CallbackQueryHandler(cancelar_finanza_callback, pattern="^cancelar_finanza$"),
        ],
        allow_reentry=True,
    )
