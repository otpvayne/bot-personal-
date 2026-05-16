"""Gestor de Firebase Realtime Database. Centraliza todas las operaciones de BD."""

import json
import logging
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import firebase_admin
import pytz
from firebase_admin import credentials, db

from database.models import Tarea, Transaccion

logger = logging.getLogger(__name__)

TIMEZONE = "America/Bogota"
_tz = pytz.timezone(TIMEZONE)


# ---------------------------------------------------------------------------
# Inicialización del SDK
# ---------------------------------------------------------------------------

def _inicializar_firebase() -> None:
    """Inicializa la app de Firebase una sola vez (idempotente)."""
    if firebase_admin._apps:
        return

    db_url = os.getenv("FIREBASE_DB_URL")
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./serviceAccountKey.json")
    cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")  # alternativa: JSON como string en var

    if not db_url:
        raise EnvironmentError("FIREBASE_DB_URL no está configurada.")

    if cred_json:
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
    elif os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
    else:
        raise EnvironmentError(
            f"Credenciales de Firebase no encontradas. "
            f"Define FIREBASE_CREDENTIALS_JSON o coloca el archivo en {cred_path}"
        )

    firebase_admin.initialize_app(cred, {"databaseURL": db_url})
    logger.info("Firebase inicializado correctamente.")


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------

class FirebaseManager:
    """
    Interfaz de alto nivel para la base de datos.

    Estructura en Firebase:
        usuarios/{user_id}/info/
        usuarios/{user_id}/tareas/{task_id}/
        usuarios/{user_id}/transacciones/{tx_id}/
    """

    def __init__(self) -> None:
        _inicializar_firebase()

    # ------------------------------------------------------------------
    # Helpers de referencias
    # ------------------------------------------------------------------

    def _ref_usuario(self, user_id: int) -> db.Reference:
        return db.reference(f"usuarios/{user_id}")

    def _ref_tareas(self, user_id: int) -> db.Reference:
        return db.reference(f"usuarios/{user_id}/tareas")

    def _ref_tarea(self, user_id: int, task_id: str) -> db.Reference:
        return db.reference(f"usuarios/{user_id}/tareas/{task_id}")

    def _ref_transacciones(self, user_id: int) -> db.Reference:
        return db.reference(f"usuarios/{user_id}/transacciones")

    def _ref_transaccion(self, user_id: int, tx_id: str) -> db.Reference:
        return db.reference(f"usuarios/{user_id}/transacciones/{tx_id}")

    # ------------------------------------------------------------------
    # Gestión de usuario
    # ------------------------------------------------------------------

    def registrar_usuario(self, user_id: int, nombre: str) -> None:
        """Registra o actualiza la info básica del usuario."""
        ref = self._ref_usuario(user_id).child("info")
        existing = ref.get()
        if not existing:
            ref.set({
                "nombre": nombre,
                "telegram_id": user_id,
                "fecha_registro": datetime.now(_tz).isoformat(),
            })

    def obtener_todos_usuarios(self) -> List[int]:
        """Retorna lista de todos los user_ids registrados."""
        data = db.reference("usuarios").get()
        if not data:
            return []
        return [int(uid) for uid in data.keys()]

    # ------------------------------------------------------------------
    # Tareas — escritura
    # ------------------------------------------------------------------

    def crear_tarea(self, user_id: int, tarea: Tarea) -> Tarea:
        """Guarda una tarea nueva en Firebase."""
        self._ref_tarea(user_id, tarea.id).set(tarea.to_dict())
        logger.info("Tarea creada: user=%s id=%s", user_id, tarea.id)
        return tarea

    def completar_tarea(self, user_id: int, task_id: str) -> bool:
        """Marca una tarea como completada. Retorna False si no existe."""
        ref = self._ref_tarea(user_id, task_id)
        if not ref.get():
            return False
        ref.update({
            "estado": "completada",
            "fecha_completada": datetime.now(_tz).isoformat(),
        })
        return True

    def eliminar_tarea(self, user_id: int, task_id: str) -> bool:
        """Elimina una tarea. Retorna False si no existe."""
        ref = self._ref_tarea(user_id, task_id)
        if not ref.get():
            return False
        ref.delete()
        return True

    # ------------------------------------------------------------------
    # Tareas — lectura
    # ------------------------------------------------------------------

    def _get_tareas_raw(self, user_id: int) -> List[Dict]:
        data = self._ref_tareas(user_id).get()
        if not data:
            return []
        return list(data.values())

    def listar_tareas_pendientes(self, user_id: int) -> List[Dict]:
        tareas = self._get_tareas_raw(user_id)
        pendientes = [t for t in tareas if t.get("estado") == "pendiente"]
        # Ordenar: prioridad crítica primero, luego por fecha
        orden_prio = {"crítica": 0, "alta": 1, "media": 2, "baja": 3}
        return sorted(
            pendientes,
            key=lambda t: (
                orden_prio.get(t.get("prioridad", "media"), 2),
                t.get("fecha_vencimiento", "9999-12-31"),
            ),
        )

    def listar_tareas_por_fecha(self, user_id: int, fecha: date) -> List[Dict]:
        pendientes = self.listar_tareas_pendientes(user_id)
        fecha_str = fecha.strftime("%Y-%m-%d")
        return [t for t in pendientes if t.get("fecha_vencimiento") == fecha_str]

    def listar_tareas_semana(self, user_id: int) -> List[Dict]:
        pendientes = self.listar_tareas_pendientes(user_id)
        hoy = datetime.now(_tz).date()
        fin = hoy + timedelta(days=7)
        resultado = []
        for t in pendientes:
            try:
                fv = datetime.strptime(t.get("fecha_vencimiento", ""), "%Y-%m-%d").date()
                if hoy <= fv <= fin:
                    resultado.append(t)
            except ValueError:
                pass
        return resultado

    def contar_tareas_hoy(self, user_id: int) -> int:
        hoy = datetime.now(_tz).date()
        return len(self.listar_tareas_por_fecha(user_id, hoy))

    def buscar_tarea(self, user_id: int, task_id: str) -> Optional[Dict]:
        return self._ref_tarea(user_id, task_id).get()

    # ------------------------------------------------------------------
    # Finanzas — escritura
    # ------------------------------------------------------------------

    def crear_transaccion(self, user_id: int, tx: Transaccion) -> Transaccion:
        """Guarda una transacción nueva en Firebase."""
        self._ref_transaccion(user_id, tx.id).set(tx.to_dict())
        logger.info("Transacción creada: user=%s tipo=%s monto=%s", user_id, tx.tipo, tx.monto)
        return tx

    # ------------------------------------------------------------------
    # Finanzas — lectura
    # ------------------------------------------------------------------

    def _get_transacciones_raw(self, user_id: int) -> List[Dict]:
        data = self._ref_transacciones(user_id).get()
        if not data:
            return []
        txs = list(data.values())
        # Ordenar por fecha descendente
        return sorted(txs, key=lambda x: x.get("fecha", ""), reverse=True)

    def historial(self, user_id: int, limite: int = 20) -> List[Dict]:
        """Retorna las últimas `limite` transacciones."""
        return self._get_transacciones_raw(user_id)[:limite]

    def balance_total(self, user_id: int) -> Tuple[float, float]:
        """Retorna (total_ingresos, total_gastos) de todos los tiempos."""
        txs = self._get_transacciones_raw(user_id)
        ingresos = sum(t["monto"] for t in txs if t.get("tipo") == "ingreso")
        gastos = sum(t["monto"] for t in txs if t.get("tipo") == "gasto")
        return ingresos, gastos

    def balance_mes(self, user_id: int, mes: str) -> Tuple[float, float]:
        """
        Retorna (ingresos, gastos) para un mes dado.
        `mes` en formato 'YYYY-MM'.
        """
        txs = self._get_transacciones_raw(user_id)
        filtradas = [t for t in txs if t.get("mes") == mes]
        ingresos = sum(t["monto"] for t in filtradas if t.get("tipo") == "ingreso")
        gastos = sum(t["monto"] for t in filtradas if t.get("tipo") == "gasto")
        return ingresos, gastos

    def detalle_mes_por_categoria(
        self, user_id: int, mes: str
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Retorna (ingresos_por_cat, gastos_por_cat) para un mes dado.
        """
        txs = self._get_transacciones_raw(user_id)
        filtradas = [t for t in txs if t.get("mes") == mes]
        ingresos_cat: Dict[str, float] = defaultdict(float)
        gastos_cat: Dict[str, float] = defaultdict(float)
        for t in filtradas:
            cat = t.get("categoria", "Otros")
            if t.get("tipo") == "ingreso":
                ingresos_cat[cat] += t.get("monto", 0)
            else:
                gastos_cat[cat] += t.get("monto", 0)
        return dict(ingresos_cat), dict(gastos_cat)

    def resumen_por_categoria(
        self, user_id: int
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Retorna (ingresos_por_cat, gastos_por_cat) de todos los tiempos."""
        txs = self._get_transacciones_raw(user_id)
        ingresos_cat: Dict[str, float] = defaultdict(float)
        gastos_cat: Dict[str, float] = defaultdict(float)
        for t in txs:
            cat = t.get("categoria", "Otros")
            if t.get("tipo") == "ingreso":
                ingresos_cat[cat] += t.get("monto", 0)
            else:
                gastos_cat[cat] += t.get("monto", 0)
        return dict(ingresos_cat), dict(gastos_cat)
