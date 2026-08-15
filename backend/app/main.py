"""Aplicación FastAPI de Patitas Conectadas.

Se ejecuta igual en local (`uvicorn backend.app.main:app --reload`) que como
función serverless en Vercel (`api/index.py`).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_db
from .models import ALLOWED_STATUSES, ARTICLE_CATEGORIES, POST_TYPES, SPECIES
from .routers import admin, auth, cron, geo, meta, news, posts, reports, uploads, visits
from .utils import SPECIES_LABELS, STATUS_LABELS, TYPE_LABELS

logger = logging.getLogger("patitas")

AUTO_CREATE_TABLES = os.environ.get("AUTO_CREATE_TABLES", "1") != "0"


@asynccontextmanager
async def lifespan(_: FastAPI):
    if AUTO_CREATE_TABLES:
        try:
            init_db()
        except Exception as exc:  # pragma: no cover - depende de la base de datos
            logger.error("No se pudieron crear/verificar las tablas: %s", exc)
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    description="Plataforma de mascotas perdidas, encontradas y en adopción.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mensajes claros para los campos que el usuario ve en el formulario
MENSAJES_POR_CAMPO = {
    "photos": "Agrega al menos una foto para ayudar a identificar a la mascota.",
    "description": "Escribe una descripción breve (mínimo 10 caracteres).",
    "location.city": "Selecciona la ciudad.",
    "event_date": "Indica la fecha en que ocurrió.",
    "species": "Selecciona la especie de la mascota.",
    "type": "Selecciona el tipo de publicación.",
    "contact": "Agrega al menos un medio de contacto: WhatsApp, teléfono o correo.",
    "contact.email": "El correo de contacto no es válido.",
    "email": "El correo no es válido.",
    "password": "La contraseña debe tener al menos 8 caracteres.",
}

MENSAJES_POR_TIPO = {
    "missing": "Falta completar este dato.",
    "string_too_short": "El texto es demasiado corto.",
    "string_too_long": "El texto es demasiado largo.",
    "too_short": "Falta información en esta lista.",
    "too_long": "Enviaste más elementos de los permitidos.",
    "value_error": "Revisa este dato.",
}


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Convierte los errores de validación en un mensaje legible en español."""
    errores = []
    for error in exc.errors():
        campo = ".".join(str(parte) for parte in error.get("loc", [])[1:]) or "formulario"
        tipo = error.get("type", "")
        mensaje = str(error.get("msg", "")).replace("Value error, ", "").strip()

        # Los validadores propios ya devuelven un mensaje en español: se respeta.
        if tipo != "value_error":
            if campo in MENSAJES_POR_CAMPO:
                mensaje = MENSAJES_POR_CAMPO[campo]
            elif tipo in MENSAJES_POR_TIPO:
                mensaje = MENSAJES_POR_TIPO[tipo]
        errores.append({"campo": campo, "mensaje": mensaje})

    principal = errores[0] if errores else {"campo": "formulario", "mensaje": "Revisa los datos enviados."}
    return JSONResponse(
        status_code=422,
        content={"detail": principal["mensaje"], "campo": principal["campo"], "errores": errores},
    )


# Fotos guardadas en disco durante el desarrollo (en producción se usa Vercel Blob).
# El disco puede ser de solo lectura (serverless): si falla, se sigue sin montar /uploads.
if not settings.blob_token:
    try:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
    except OSError as exc:
        logger.error("No se pudo preparar la carpeta de subidas (%s): %s", settings.upload_dir, exc)


app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(uploads.router)
app.include_router(reports.router)
app.include_router(geo.router)
app.include_router(news.router)
app.include_router(news.feed_router)
app.include_router(admin.router)
app.include_router(visits.router)
app.include_router(cron.router)
app.include_router(meta.router)


@app.get("/api/health", tags=["sistema"])
def health() -> dict:
    # `database` no expone credenciales: solo el motor en uso. En serverless, "sqlite"
    # significa que falta definir DATABASE_URL y ninguna consulta va a funcionar.
    return {
        "ok": True,
        "app": settings.app_name,
        "environment": settings.environment,
        "database": "sqlite" if settings.is_sqlite else "postgresql",
    }


@app.get("/api/config", tags=["sistema"])
def public_config() -> dict:
    """Catálogos y textos que el frontend necesita para construir los formularios."""
    return {
        "app_name": settings.app_name,
        "site_url": settings.site_url,
        "max_photos": settings.max_photos,
        "types": [
            {"value": t, "label": TYPE_LABELS[t], "statuses": [
                {"value": s, "label": STATUS_LABELS[s]} for s in ALLOWED_STATUSES[t]
            ]}
            for t in POST_TYPES
        ],
        "species": [{"value": s, "label": SPECIES_LABELS[s]} for s in SPECIES],
        "sexes": [
            {"value": "macho", "label": "Macho"},
            {"value": "hembra", "label": "Hembra"},
            {"value": "desconocido", "label": "No lo sé"},
        ],
        "sizes": [
            {"value": "pequeno", "label": "Pequeño"},
            {"value": "mediano", "label": "Mediano"},
            {"value": "grande", "label": "Grande"},
        ],
        "article_categories": list(ARTICLE_CATEGORIES),
        "captcha_enabled": bool(settings.turnstile_secret),
        "captcha_site_key": os.environ.get("TURNSTILE_SITE_KEY", ""),
    }
