"""Modelos de datos: Tarea y Transacción."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pytz

TIMEZONE = "America/Bogota"
_tz = pytz.timezone(TIMEZONE)


def _now_iso() -> str:
    return datetime.now(_tz).isoformat()


def _nuevo_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Tarea
# ---------------------------------------------------------------------------

@dataclass
class Tarea:
    nombre: str
    fecha_vencimiento: str                 # YYYY-MM-DD
    prioridad: str = "media"               # baja | media | alta | crítica
    descripcion: str = ""
    estado: str = "pendiente"              # pendiente | completada
    id: str = field(default_factory=_nuevo_id)
    fecha_creacion: str = field(default_factory=_now_iso)
    fecha_completada: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "fecha_vencimiento": self.fecha_vencimiento,
            "prioridad": self.prioridad,
            "estado": self.estado,
            "fecha_creacion": self.fecha_creacion,
            "fecha_completada": self.fecha_completada,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Tarea":
        return cls(
            id=data.get("id", _nuevo_id()),
            nombre=data.get("nombre", ""),
            descripcion=data.get("descripcion", ""),
            fecha_vencimiento=data.get("fecha_vencimiento", ""),
            prioridad=data.get("prioridad", "media"),
            estado=data.get("estado", "pendiente"),
            fecha_creacion=data.get("fecha_creacion", _now_iso()),
            fecha_completada=data.get("fecha_completada"),
        )


# ---------------------------------------------------------------------------
# Transacción financiera
# ---------------------------------------------------------------------------

@dataclass
class Transaccion:
    tipo: str                              # ingreso | gasto
    monto: float
    categoria: str
    descripcion: str = ""
    id: str = field(default_factory=_nuevo_id)
    fecha: str = field(default_factory=_now_iso)
    mes: str = field(default_factory=lambda: datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "monto": self.monto,
            "categoria": self.categoria,
            "descripcion": self.descripcion,
            "fecha": self.fecha,
            "mes": self.mes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaccion":
        return cls(
            id=data.get("id", _nuevo_id()),
            tipo=data.get("tipo", "gasto"),
            monto=float(data.get("monto", 0)),
            categoria=data.get("categoria", "Otros"),
            descripcion=data.get("descripcion", ""),
            fecha=data.get("fecha", _now_iso()),
            mes=data.get("mes", ""),
        )
