"""Contador de visitas al sitio.

El frontend avisa en cada cambio de pantalla. Se guarda únicamente un total por
día: ni IP, ni identificador, ni ruta. Sirve para responder «¿nos está viendo
alguien?», no para perfilar a nadie.

Ojo con lo que mide: es un contador propio, no una herramienta de analítica.
Cuenta lo que el navegador reporta, así que los bots que no ejecutan JavaScript
no aparecen y cualquiera podría inflarlo llamando al endpoint. Para cifras
serias conviene apoyarse además en Vercel Analytics.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SiteVisit
from ..schemas import VisitIn
from ..utils import client_ip, rate_limit_ok

router = APIRouter(prefix="/api/visits", tags=["métricas"])

# Tope por IP: una persona navegando rápido no llega a esto, pero corta el abuso.
LIMITE_POR_IP = 240
VENTANA_SEGUNDOS = 600


def _sumar_visita(db: Session, *, nueva_sesion: bool) -> None:
    """Suma 1 al contador de hoy, creando la fila del día si aún no existe."""
    hoy = date.today()
    incremento_sesion = 1 if nueva_sesion else 0

    def intentar_actualizar() -> int:
        resultado = db.execute(
            update(SiteVisit)
            .where(SiteVisit.day == hoy)
            .values(views=SiteVisit.views + 1, sessions=SiteVisit.sessions + incremento_sesion)
        )
        return resultado.rowcount or 0

    if intentar_actualizar():
        db.commit()
        return

    # Primera visita del día: se crea la fila. Si otra petición se adelantó,
    # el UNIQUE de la clave primaria falla y se reintenta el UPDATE.
    try:
        db.add(SiteVisit(day=hoy, views=1, sessions=incremento_sesion))
        db.commit()
    except IntegrityError:
        db.rollback()
        intentar_actualizar()
        db.commit()


@router.post("", status_code=204, response_model=None)
def registrar_visita(payload: VisitIn, request: Request, db: Session = Depends(get_db)) -> None:
    if not rate_limit_ok(f"visita:{client_ip(request)}", LIMITE_POR_IP, VENTANA_SEGUNDOS):
        return
    try:
        _sumar_visita(db, nueva_sesion=payload.new_session)
    except Exception:  # pragma: no cover - una métrica nunca debe romper la navegación
        db.rollback()


VISITAS_VACIAS = {
    "total": 0,
    "sessions_total": 0,
    "today": 0,
    "last_7_days": 0,
    "last_30_days": 0,
    "sessions_last_7_days": 0,
    "daily": [],
    "unavailable": True,
}


def resumen_visitas(db: Session) -> dict:
    """Totales para el panel de administración.

    Si la tabla `site_visits` todavía no existe (por ejemplo, con
    AUTO_CREATE_TABLES=0 en una base que se migró antes de esta versión), se
    devuelven ceros en lugar de tumbar todo el panel por una métrica.
    """
    try:
        return _resumen_visitas(db)
    except Exception:  # pragma: no cover - depende del estado de la base
        db.rollback()
        return dict(VISITAS_VACIAS)


def _resumen_visitas(db: Session) -> dict:
    hoy = date.today()
    hace_7 = hoy - timedelta(days=6)   # incluye hoy
    hace_30 = hoy - timedelta(days=29)

    def sumar(campo, desde: date | None = None) -> int:
        consulta = select(func.coalesce(func.sum(campo), 0))
        if desde is not None:
            consulta = consulta.where(SiteVisit.day >= desde)
        return int(db.scalar(consulta) or 0)

    fila_hoy = db.get(SiteVisit, hoy)

    ultimos_dias = db.execute(
        select(SiteVisit.day, SiteVisit.views, SiteVisit.sessions)
        .where(SiteVisit.day >= hace_7)
        .order_by(SiteVisit.day)
    ).all()

    return {
        "total": sumar(SiteVisit.views),
        "sessions_total": sumar(SiteVisit.sessions),
        "today": fila_hoy.views if fila_hoy else 0,
        "last_7_days": sumar(SiteVisit.views, hace_7),
        "last_30_days": sumar(SiteVisit.views, hace_30),
        "sessions_last_7_days": sumar(SiteVisit.sessions, hace_7),
        "daily": [
            {"day": fila.day.isoformat(), "views": fila.views, "sessions": fila.sessions}
            for fila in ultimos_dias
        ],
    }
