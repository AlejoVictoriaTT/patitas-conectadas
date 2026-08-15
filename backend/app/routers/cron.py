"""Tareas programadas que dispara Vercel Cron.

Vercel llama estas rutas por HTTP según el bloque `crons` de `vercel.json`, y
añade la cabecera `Authorization: Bearer $CRON_SECRET` cuando esa variable de
entorno existe. Sin secreto configurado la ruta queda abierta, así que en
producción CRON_SECRET es obligatorio: de lo contrario cualquiera podría
disparar la ingesta a voluntad.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .. import news_feed
from ..db import get_db

logger = logging.getLogger("patitas")

router = APIRouter(prefix="/api/cron", tags=["tareas programadas"])


def verificar_secreto(authorization: str | None = Header(default=None)) -> None:
    secreto = os.environ.get("CRON_SECRET", "")
    if not secreto:
        # Sin secreto se permite solo fuera de producción, para poder probar.
        if os.environ.get("VERCEL_ENV") == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Falta configurar CRON_SECRET.",
            )
        return
    if authorization != f"Bearer {secreto}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado.")


@router.get("/news", dependencies=[Depends(verificar_secreto)])
async def sincronizar_noticias(db: Session = Depends(get_db)) -> dict:
    """Trae las noticias nuevas de los medios. Idempotente: repetirla no duplica."""
    resumen = await news_feed.sincronizar(db)
    logger.info("Ingesta de noticias: %s", resumen)
    return {"ok": True, **resumen}
