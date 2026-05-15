"""Funciones para formatear mensajes de Telegram con emojis y estructura."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz

from utils.constants import CATEGORIAS_GASTO, CATEGORIAS_INGRESO, PRIORIDADES, TIMEZONE

_tz = pytz.timezone(TIMEZONE)


# ---------------------------------------------------------------------------
# Helpers generales
# ---------------------------------------------------------------------------

def fmt_monto(monto: float) -> str:
    """Formatea un número como moneda colombiana: $1.234.567."""
    entero = int(round(monto))
    return f"${entero:,}".replace(",", ".")


def fmt_fecha(fecha_str: str) -> str:
    """Convierte 'YYYY-MM-DD' a '15 de mayo de 2025'."""
    try:
        d = datetime.strptime(fecha_str, "%Y-%m-%d")
        meses = [
            "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        return f"{d.day} de {meses[d.month]} de {d.year}"
    except (ValueError, AttributeError):
        return fecha_str


def fmt_timestamp(ts: Any) -> str:
    """Convierte un timestamp ISO o Unix a cadena legible."""
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts, tz=_tz)
        else:
            dt = datetime.fromisoformat(str(ts)).astimezone(_tz)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


def emoji_prioridad(prioridad: str) -> str:
    return PRIORIDADES.get(prioridad.lower(), "⚪")


def emoji_categoria_gasto(categoria: str) -> str:
    return CATEGORIAS_GASTO.get(categoria, "📌")


def emoji_categoria_ingreso(categoria: str) -> str:
    return CATEGORIAS_INGRESO.get(categoria, "📌")


# ---------------------------------------------------------------------------
# Formateo de Tareas
# ---------------------------------------------------------------------------

def formatear_tarea(tarea: Dict) -> str:
    """Formatea una sola tarea para mostrar en el listado."""
    emoji = emoji_prioridad(tarea.get("prioridad", "media"))
    prioridad = tarea.get("prioridad", "media").upper()
    nombre = tarea.get("nombre", "(sin nombre)")
    vence = fmt_fecha(tarea.get("fecha_vencimiento", ""))
    creada = fmt_timestamp(tarea.get("fecha_creacion", ""))
    task_id = tarea.get("id", "?")
    desc = tarea.get("descripcion", "")

    lineas = [
        f"{emoji} [{prioridad}] {nombre}",
        f"   ├─ Vence: {vence}",
        f"   ├─ Creada: {creada}",
    ]
    if desc:
        lineas.append(f"   ├─ Nota: {desc}")
    lineas.append(f"   └─ ID: `{task_id}`")

    return "\n".join(lineas)


def formatear_lista_tareas(tareas: List[Dict], titulo: str = "TUS TAREAS PENDIENTES") -> str:
    """Formatea la lista completa de tareas."""
    if not tareas:
        return "✅ No tienes tareas pendientes. ¡Estás al día!"

    bloques = [f"📋 *{titulo}:*\n"]
    for tarea in tareas:
        bloques.append(formatear_tarea(tarea))

    total = len(tareas)
    bloques.append(f"\nTotal: {total} tarea{'s' if total != 1 else ''} pendiente{'s' if total != 1 else ''}")
    bloques.append("Usa `/completar ID` para marcar como hecha")
    return "\n".join(bloques)


# ---------------------------------------------------------------------------
# Formateo de Finanzas
# ---------------------------------------------------------------------------

def formatear_transaccion(tx: Dict, numero: int) -> str:
    """Formatea una transacción para el historial."""
    es_ingreso = tx.get("tipo") == "ingreso"
    signo = "✅ [+" if es_ingreso else "❌ [-"
    monto_str = fmt_monto(tx.get("monto", 0))
    categoria = tx.get("categoria", "Otros")
    tipo_label = "INGRESO" if es_ingreso else "GASTO"
    fecha = fmt_timestamp(tx.get("fecha", ""))
    desc = tx.get("descripcion", "")

    lineas = [
        f"{numero}. {signo}{monto_str}] {tipo_label} - {categoria}",
        f"   📅 {fecha}",
    ]
    if desc:
        lineas.append(f"   📝 {desc}")
    return "\n".join(lineas)


def formatear_historial(transacciones: List[Dict]) -> str:
    """Formatea el listado de últimas transacciones."""
    if not transacciones:
        return "📭 No hay transacciones registradas aún."

    bloques = ["📊 *ÚLTIMAS TRANSACCIONES:*\n"]
    for i, tx in enumerate(transacciones, 1):
        bloques.append(formatear_transaccion(tx, i))

    bloques.append("\nUsa `/balance` para ver resumen")
    return "\n".join(bloques)


def formatear_balance(
    total_ingresos: float,
    total_gastos: float,
    mes_ingresos: float,
    mes_gastos: float,
    mes_label: str,
) -> str:
    """Formatea el balance completo."""
    neto = total_ingresos - total_gastos
    saldo_mes = mes_ingresos - mes_gastos
    icono_neto = "✅" if neto >= 0 else "⚠️"
    icono_mes = "✅" if saldo_mes >= 0 else "⚠️"

    return (
        f"💰 *BALANCE ACTUAL:*\n\n"
        f"📈 INGRESOS TOTALES: {fmt_monto(total_ingresos)}\n"
        f"📉 GASTOS TOTALES: {fmt_monto(total_gastos)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{icono_neto} BALANCE NETO: {fmt_monto(neto)}\n\n"
        f"📅 *MES ACTUAL ({mes_label.upper()}):*\n"
        f"  📈 Ingresos: {fmt_monto(mes_ingresos)}\n"
        f"  📉 Gastos: {fmt_monto(mes_gastos)}\n"
        f"  {icono_mes} Saldo mes: {fmt_monto(saldo_mes)}\n\n"
        f"Usa `/historial` para ver transacciones\n"
        f"Usa `/categoria` para ver resumen por categoría"
    )


def formatear_resumen_mes(
    mes_label: str,
    ingresos: float,
    gastos: float,
    detalle_ingresos: Dict[str, float],
    detalle_gastos: Dict[str, float],
) -> str:
    """Formatea el reporte de un mes específico."""
    saldo = ingresos - gastos
    icono = "✅" if saldo >= 0 else "⚠️"

    lineas = [
        f"📅 *RESUMEN {mes_label.upper()}:*\n",
        f"📈 Ingresos totales: {fmt_monto(ingresos)}",
        f"📉 Gastos totales: {fmt_monto(gastos)}",
        f"{icono} Saldo: {fmt_monto(saldo)}\n",
    ]

    if detalle_ingresos:
        lineas.append("*Ingresos por categoría:*")
        for cat, total in sorted(detalle_ingresos.items(), key=lambda x: -x[1]):
            emoji = emoji_categoria_ingreso(cat)
            lineas.append(f"  {emoji} {cat}: {fmt_monto(total)}")
        lineas.append("")

    if detalle_gastos:
        lineas.append("*Gastos por categoría:*")
        for cat, total in sorted(detalle_gastos.items(), key=lambda x: -x[1]):
            emoji = emoji_categoria_gasto(cat)
            lineas.append(f"  {emoji} {cat}: {fmt_monto(total)}")

    return "\n".join(lineas)


def formatear_categoria(
    ingresos_cat: Dict[str, float],
    gastos_cat: Dict[str, float],
) -> str:
    """Formatea el resumen de todas las categorías."""
    lineas = ["📊 *RESUMEN POR CATEGORÍA:*\n"]

    if ingresos_cat:
        lineas.append("📈 *INGRESOS:*")
        for cat, total in sorted(ingresos_cat.items(), key=lambda x: -x[1]):
            emoji = emoji_categoria_ingreso(cat)
            lineas.append(f"  {emoji} {cat}: {fmt_monto(total)}")
        lineas.append("")

    if gastos_cat:
        lineas.append("📉 *GASTOS:*")
        for cat, total in sorted(gastos_cat.items(), key=lambda x: -x[1]):
            emoji = emoji_categoria_gasto(cat)
            lineas.append(f"  {emoji} {cat}: {fmt_monto(total)}")

    if not ingresos_cat and not gastos_cat:
        return "📭 No hay transacciones registradas aún."

    return "\n".join(lineas)


def formatear_reporte_completo(
    total_ingresos: float,
    total_gastos: float,
    mes_ingresos: float,
    mes_gastos: float,
    mes_label: str,
    ingresos_cat: Dict[str, float],
    gastos_cat: Dict[str, float],
    tareas_pendientes: int,
    tareas_hoy: int,
) -> str:
    """Genera un reporte completo de todo."""
    neto = total_ingresos - total_gastos
    saldo_mes = mes_ingresos - mes_gastos

    lineas = [
        "📊 *REPORTE COMPLETO*\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "💰 *FINANZAS TOTALES:*",
        f"  📈 Ingresos: {fmt_monto(total_ingresos)}",
        f"  📉 Gastos: {fmt_monto(total_gastos)}",
        f"  {'✅' if neto >= 0 else '⚠️'} Neto: {fmt_monto(neto)}\n",
        f"📅 *MES ACTUAL ({mes_label.upper()}):*",
        f"  📈 Ingresos: {fmt_monto(mes_ingresos)}",
        f"  📉 Gastos: {fmt_monto(mes_gastos)}",
        f"  {'✅' if saldo_mes >= 0 else '⚠️'} Saldo: {fmt_monto(saldo_mes)}\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "📋 *TAREAS:*",
        f"  📌 Pendientes: {tareas_pendientes}",
        f"  📅 Vencen hoy: {tareas_hoy}\n",
    ]

    if ingresos_cat:
        lineas.append("📈 *Top categorías de ingreso:*")
        for cat, total in sorted(ingresos_cat.items(), key=lambda x: -x[1])[:3]:
            emoji = emoji_categoria_ingreso(cat)
            lineas.append(f"  {emoji} {cat}: {fmt_monto(total)}")
        lineas.append("")

    if gastos_cat:
        lineas.append("📉 *Top categorías de gasto:*")
        for cat, total in sorted(gastos_cat.items(), key=lambda x: -x[1])[:3]:
            emoji = emoji_categoria_gasto(cat)
            lineas.append(f"  {emoji} {cat}: {fmt_monto(total)}")

    return "\n".join(lineas)
