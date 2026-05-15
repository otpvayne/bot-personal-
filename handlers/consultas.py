"""Handlers para consultas de balance, historial, reportes y categorías."""

import logging
from datetime import datetime

import pytz
from telegram import Update
from telegram.ext import ContextTypes

from database.utils import get_manager, verificar_rate_limit
from utils.formatters import (
    formatear_balance,
    formatear_categoria,
    formatear_historial,
    formatear_reporte_completo,
    formatear_resumen_mes,
)
from utils.validators import es_chat_privado
from utils.constants import HISTORIAL_DEFAULT, HISTORIAL_MAX

logger = logging.getLogger(__name__)
TIMEZONE = "America/Bogota"
_tz = pytz.timezone(TIMEZONE)

_MESES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _mes_label(mes_str: str) -> str:
    """Convierte 'YYYY-MM' en 'mayo 2025'."""
    try:
        dt = datetime.strptime(mes_str, "%Y-%m")
        return f"{_MESES[dt.month]} {dt.year}"
    except ValueError:
        return mes_str


# ---------------------------------------------------------------------------
# /balance
# ---------------------------------------------------------------------------

async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    mes_actual = datetime.now(_tz).strftime("%Y-%m")
    label = _mes_label(mes_actual)

    try:
        manager = get_manager()
        total_ing, total_gas = manager.balance_total(user.id)
        mes_ing, mes_gas = manager.balance_mes(user.id, mes_actual)
    except Exception as e:
        logger.error("Error obteniendo balance: %s", e)
        await update.message.reply_text("❌ Error al obtener el balance.")
        return

    mensaje = formatear_balance(total_ing, total_gas, mes_ing, mes_gas, label)
    await update.message.reply_text(mensaje, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /historial
# ---------------------------------------------------------------------------

async def cmd_historial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    # Parsear límite opcional
    limite = HISTORIAL_DEFAULT
    if context.args:
        try:
            limite = min(int(context.args[0]), HISTORIAL_MAX)
        except ValueError:
            await update.message.reply_text("❌ Uso: `/historial` o `/historial 50`", parse_mode="Markdown")
            return

    try:
        txs = get_manager().historial(user.id, limite)
    except Exception as e:
        logger.error("Error obteniendo historial: %s", e)
        await update.message.reply_text("❌ Error al obtener el historial.")
        return

    mensaje = formatear_historial(txs)
    await update.message.reply_text(mensaje, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /mes — resumen mensual
# ---------------------------------------------------------------------------

async def cmd_mes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    ahora = datetime.now(_tz)

    if not context.args or context.args[0].lower() in ("actual", "current"):
        mes_str = ahora.strftime("%Y-%m")
    else:
        arg = context.args[0].zfill(2)  # '5' → '05'
        try:
            num_mes = int(arg)
            if not 1 <= num_mes <= 12:
                raise ValueError()
            year = ahora.year
            # Si el mes solicitado es futuro, asumir año anterior
            if num_mes > ahora.month:
                year -= 1
            mes_str = f"{year}-{arg}"
        except ValueError:
            await update.message.reply_text(
                "❌ Uso: `/mes actual` o `/mes MM` (ej: `/mes 05`)",
                parse_mode="Markdown",
            )
            return

    label = _mes_label(mes_str)
    try:
        manager = get_manager()
        ingresos, gastos = manager.balance_mes(user.id, mes_str)
        ing_cat, gas_cat = manager.detalle_mes_por_categoria(user.id, mes_str)
    except Exception as e:
        logger.error("Error obteniendo resumen mensual: %s", e)
        await update.message.reply_text("❌ Error al obtener el resumen mensual.")
        return

    mensaje = formatear_resumen_mes(label, ingresos, gastos, ing_cat, gas_cat)
    await update.message.reply_text(mensaje, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /categoria
# ---------------------------------------------------------------------------

async def cmd_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    try:
        ing_cat, gas_cat = get_manager().resumen_por_categoria(user.id)
    except Exception as e:
        logger.error("Error obteniendo categorías: %s", e)
        await update.message.reply_text("❌ Error al obtener el resumen por categoría.")
        return

    mensaje = formatear_categoria(ing_cat, gas_cat)
    await update.message.reply_text(mensaje, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /reporte
# ---------------------------------------------------------------------------

async def cmd_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not es_chat_privado(update):
        return
    user = update.effective_user
    if not verificar_rate_limit(user.id):
        await update.message.reply_text("⏳ Demasiados comandos.")
        return

    mes_actual = datetime.now(_tz).strftime("%Y-%m")
    label = _mes_label(mes_actual)

    try:
        manager = get_manager()
        total_ing, total_gas = manager.balance_total(user.id)
        mes_ing, mes_gas = manager.balance_mes(user.id, mes_actual)
        ing_cat, gas_cat = manager.resumen_por_categoria(user.id)
        tareas_pendientes = len(manager.listar_tareas_pendientes(user.id))
        tareas_hoy = manager.contar_tareas_hoy(user.id)
    except Exception as e:
        logger.error("Error generando reporte: %s", e)
        await update.message.reply_text("❌ Error al generar el reporte.")
        return

    mensaje = formatear_reporte_completo(
        total_ing, total_gas,
        mes_ing, mes_gas,
        label,
        ing_cat, gas_cat,
        tareas_pendientes, tareas_hoy,
    )
    await update.message.reply_text(mensaje, parse_mode="Markdown")
