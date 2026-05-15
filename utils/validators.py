"""Validadores de entrada del usuario."""

import re
from datetime import date, datetime, timedelta
from typing import Optional, Tuple

import pytz

from utils.constants import (
    CATEGORIAS_GASTO,
    CATEGORIAS_INGRESO,
    MAX_DESC_FINANZA,
    MAX_DESC_TAREA,
    MAX_MONTO,
    MAX_NOMBRE_TAREA,
    PRIORIDADES_LISTA,
    TIMEZONE,
)


_tz = pytz.timezone(TIMEZONE)


def _hoy() -> date:
    return datetime.now(_tz).date()


def validar_nombre_tarea(nombre: str) -> Tuple[bool, str]:
    """Valida el nombre de una tarea. Retorna (ok, mensaje_error)."""
    nombre = nombre.strip()
    if not nombre:
        return False, "El nombre no puede estar vacío."
    if len(nombre) > MAX_NOMBRE_TAREA:
        return False, f"El nombre no puede superar {MAX_NOMBRE_TAREA} caracteres."
    return True, ""


def validar_fecha(texto: str) -> Tuple[bool, Optional[date], str]:
    """
    Parsea fechas en distintos formatos.
    Acepta: YYYY-MM-DD, DD/MM/YYYY, 'hoy', 'mañana'.
    Retorna (ok, fecha_date, mensaje_error).
    """
    texto = texto.strip().lower()

    if texto in ("hoy", "today"):
        return True, _hoy(), ""

    if texto in ("mañana", "manana", "tomorrow"):
        return True, _hoy() + timedelta(days=1), ""

    # Intentar formatos comunes
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    for fmt in formatos:
        try:
            parsed = datetime.strptime(texto, fmt).date()
            if parsed < _hoy():
                return False, None, "La fecha no puede ser en el pasado."
            return True, parsed, ""
        except ValueError:
            continue

    return False, None, "Formato de fecha inválido. Usa YYYY-MM-DD, hoy o mañana."


def validar_prioridad(texto: str) -> Tuple[bool, str, str]:
    """Valida la prioridad. Retorna (ok, prioridad_normalizada, mensaje_error)."""
    texto = texto.strip().lower()
    # Permitir abreviaciones
    mapeo = {
        "c": "crítica", "critica": "crítica", "crítica": "crítica",
        "a": "alta", "alta": "alta",
        "m": "media", "media": "media",
        "b": "baja", "baja": "baja",
    }
    normalizado = mapeo.get(texto)
    if not normalizado:
        return False, "", f"Prioridad inválida. Usa: {', '.join(PRIORIDADES_LISTA)}"
    return True, normalizado, ""


def validar_descripcion_tarea(texto: str) -> Tuple[bool, str, str]:
    """Valida descripción de tarea (opcional). Retorna (ok, descripcion, mensaje_error)."""
    texto = texto.strip()
    if len(texto) > MAX_DESC_TAREA:
        return False, "", f"La descripción no puede superar {MAX_DESC_TAREA} caracteres."
    return True, texto, ""


def validar_monto(texto: str) -> Tuple[bool, float, str]:
    """
    Valida y parsea un monto monetario.
    Acepta: 20000, 20.000, 20,000, 1500.50
    Retorna (ok, monto_float, mensaje_error).
    """
    texto = texto.strip()
    # Remover separadores de miles
    texto_limpio = re.sub(r"[,.](?=\d{3}(?:[,.]|$))", "", texto)
    # Reemplazar coma decimal por punto
    texto_limpio = texto_limpio.replace(",", ".")

    try:
        monto = float(texto_limpio)
    except ValueError:
        return False, 0, "El monto debe ser un número válido (ej: 20000 o 15000.50)."

    if monto <= 0:
        return False, 0, "El monto debe ser mayor a cero."
    if monto > MAX_MONTO:
        return False, 0, f"El monto no puede superar ${MAX_MONTO:,.0f}."

    return True, monto, ""


def validar_categoria_gasto(texto: str) -> Tuple[bool, str, str]:
    """Valida categoría de gasto. Retorna (ok, categoria, mensaje_error)."""
    texto = texto.strip().title()
    if texto in CATEGORIAS_GASTO:
        return True, texto, ""
    opciones = ", ".join(CATEGORIAS_GASTO.keys())
    return False, "", f"Categoría inválida. Opciones: {opciones}"


def validar_categoria_ingreso(texto: str) -> Tuple[bool, str, str]:
    """Valida categoría de ingreso. Retorna (ok, categoria, mensaje_error)."""
    texto = texto.strip().title()
    if texto in CATEGORIAS_INGRESO:
        return True, texto, ""
    opciones = ", ".join(CATEGORIAS_INGRESO.keys())
    return False, "", f"Categoría inválida. Opciones: {opciones}"


def validar_descripcion_finanza(texto: str) -> Tuple[bool, str, str]:
    """Valida descripción de transacción (opcional). Retorna (ok, descripcion, mensaje_error)."""
    texto = texto.strip()
    if len(texto) > MAX_DESC_FINANZA:
        return False, "", f"La descripción no puede superar {MAX_DESC_FINANZA} caracteres."
    return True, texto, ""


def es_chat_privado(update) -> bool:  # type: ignore[valid-type]
    """Verifica que el mensaje viene de un chat privado."""
    return update.effective_chat.type == "private"
