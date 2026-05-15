"""Constantes globales: categorías, prioridades, emojis y límites."""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Prioridades de tareas
# ---------------------------------------------------------------------------

PRIORIDADES: Dict[str, str] = {
    "crítica": "🔴",
    "alta": "🟠",
    "media": "🟡",
    "baja": "🟢",
}

PRIORIDADES_LISTA: List[str] = ["crítica", "alta", "media", "baja"]

# ---------------------------------------------------------------------------
# Categorías de finanzas
# ---------------------------------------------------------------------------

CATEGORIAS_INGRESO: Dict[str, str] = {
    "Servicios": "💼",
    "Freelance": "💻",
    "Consultoría": "📊",
    "Venta de productos": "🛒",
    "Otros": "📌",
}

CATEGORIAS_GASTO: Dict[str, str] = {
    "Comida": "🍔",
    "Transporte": "🚕",
    "Servicios": "💻",
    "Compras": "🛒",
    "Utilities": "💡",
    "Salud": "💊",
    "Entretenimiento": "🎬",
    "Otros": "📌",
}

# ---------------------------------------------------------------------------
# Estados de conversación (ConversationHandler)
# ---------------------------------------------------------------------------

# Tareas
NOMBRE_TAREA = 0
FECHA_TAREA = 1
PRIORIDAD_TAREA = 2
DESCRIPCION_TAREA = 3

# Finanzas - gasto
MONTO_GASTO = 10
CATEGORIA_GASTO = 11
DESCRIPCION_GASTO = 12

# Finanzas - ingreso
MONTO_INGRESO = 20
CATEGORIA_INGRESO = 21
DESCRIPCION_INGRESO = 22

# ---------------------------------------------------------------------------
# Límites de validación
# ---------------------------------------------------------------------------

MAX_NOMBRE_TAREA = 200
MAX_DESC_TAREA = 500
MAX_DESC_FINANZA = 200
MAX_MONTO = 999_999_999

# Historial por defecto
HISTORIAL_DEFAULT = 20
HISTORIAL_MAX = 50

# Rate limiting
RATE_LIMIT_COMANDOS = 10
RATE_LIMIT_VENTANA_SEG = 10

# ---------------------------------------------------------------------------
# Zona horaria
# ---------------------------------------------------------------------------

TIMEZONE = "America/Bogota"

# ---------------------------------------------------------------------------
# Mensajes de ayuda
# ---------------------------------------------------------------------------

MENSAJE_AYUDA = """
🤖 *BOT DE PRODUCTIVIDAD*

━━━━━━━━━━━━━━━━━━━━━━━━
📋 *TAREAS*
━━━━━━━━━━━━━━━━━━━━━━━━
`/tarea Nombre` — Crear tarea rápida
`/newtask` — Crear tarea con detalles
`/tareas` — Listar tareas pendientes
`/tareas hoy` — Tareas de hoy
`/tareas mañana` — Tareas de mañana
`/tareas semana` — Tareas esta semana
`/completar ID` — Marcar como completada
`/eliminar ID` — Eliminar tarea

━━━━━━━━━━━━━━━━━━━━━━━━
💰 *FINANZAS*
━━━━━━━━━━━━━━━━━━━━━━━━
`/gasto 20000 descripción` — Gasto rápido
`/ingreso 300000 descripción` — Ingreso rápido
`/newgasto` — Gasto con categoría
`/newingreso` — Ingreso con categoría

━━━━━━━━━━━━━━━━━━━━━━━━
📊 *CONSULTAS*
━━━━━━━━━━━━━━━━━━━━━━━━
`/balance` — Balance actual
`/historial` — Últimas 20 transacciones
`/historial 50` — Últimas 50 transacciones
`/mes actual` — Resumen del mes
`/mes 05` — Resumen de mayo
`/categoria` — Resumen por categoría
`/reporte` — Reporte completo

━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️ `/ayuda` — Ver este menú
"""
