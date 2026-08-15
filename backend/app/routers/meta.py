"""Metadatos para compartir (Open Graph), robots.txt y sitemap.xml.

Vercel reenvía a esta función únicamente las peticiones de los rastreadores
(WhatsApp, Facebook, Twitter, Google...). Las personas reciben la SPA normal,
así que no hay redirecciones ni parpadeos para el usuario final.
"""

from __future__ import annotations

from datetime import date
from html import escape
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..db import get_db
from ..models import RESOLVED_STATUSES, Post
from ..serializers import post_url
from ..utils import pet_gender, post_title, species_label, status_label, type_label

router = APIRouter(tags=["metadatos"])

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _format_date(value: date) -> str:
    return f"{value.day} de {MESES[value.month - 1]} de {value.year}"


def _render_share_page(*, title: str, description: str, image: str | None, url: str) -> HTMLResponse:
    image_tags = ""
    if image:
        image_url = image if image.startswith("http") else f"{settings.site_url}{image}"
        image_tags = (
            f'<meta property="og:image" content="{escape(image_url, quote=True)}">'
            f'<meta property="og:image:width" content="1200">'
            f'<meta property="og:image:height" content="1200">'
            f'<meta name="twitter:image" content="{escape(image_url, quote=True)}">'
        )

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description, quote=True)}">
<link rel="canonical" href="{escape(url, quote=True)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{escape(settings.app_name, quote=True)}">
<meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(description, quote=True)}">
<meta property="og:url" content="{escape(url, quote=True)}">
<meta property="og:locale" content="es_CO">
{image_tags}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{escape(title, quote=True)}">
<meta name="twitter:description" content="{escape(description, quote=True)}">
</head>
<body>
<h1>{escape(title)}</h1>
<p>{escape(description)}</p>
<p><a href="{escape(url, quote=True)}">Ver la publicación en {escape(settings.app_name)}</a></p>
</body>
</html>"""
    return HTMLResponse(html, headers={"cache-control": "public, max-age=300"})


@router.get("/mascotas/{post_type}/{slug}", include_in_schema=False)
def share_preview(post_type: str, slug: str, db: Session = Depends(get_db)) -> HTMLResponse:
    post = db.scalar(select(Post).options(selectinload(Post.photos)).where(Post.slug == slug))

    if not post or not post.is_active:
        return _render_share_page(
            title=f"{settings.app_name} — Mascotas perdidas, encontradas y en adopción",
            description="Publica y busca mascotas perdidas, encontradas y disponibles para adopción.",
            image=None,
            url=f"{settings.site_url}/mascotas/{post_type}/{slug}",
        )

    genero = pet_gender(post.species, post.sex)
    emoji = {"perdida": "🔴", "encontrada": "🟢", "adopcion": "💙"}.get(post.type, "🐾")
    title = f"{emoji} {post_title(post)} — {type_label(post.type, genero)} en {post.city}"

    partes = [
        f"{species_label(post.species)}",
        f"{status_label(post.status, genero)}",
        f"{post.city}{f', {post.region}' if post.region else ''}",
        _format_date(post.event_date),
    ]
    description = " · ".join(partes) + f". {post.description[:160]}"

    photo = post.primary_photo
    return _render_share_page(
        title=title,
        description=description,
        image=photo.url if photo else None,
        url=post_url(post),
    )


@router.get("/robots.txt", include_in_schema=False)
def robots() -> PlainTextResponse:
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /gestionar/\n"
        "Disallow: /api/\n"
        f"Sitemap: {settings.site_url}/sitemap.xml\n"
    )
    return PlainTextResponse(body)


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(db: Session = Depends(get_db)) -> Response:
    urls = [
        f"{settings.site_url}/",
        f"{settings.site_url}/buscar",
        f"{settings.site_url}/adopciones",
        f"{settings.site_url}/publicar",
        f"{settings.site_url}/noticias",
    ]

    posts = db.scalars(
        select(Post)
        .where(Post.is_active.is_(True), Post.status.notin_(RESOLVED_STATUSES))
        .order_by(Post.created_at.desc())
        .limit(2000)
    ).all()

    entries = "".join(f"<url><loc>{xml_escape(u)}</loc></url>" for u in urls)
    entries += "".join(
        f"<url><loc>{xml_escape(post_url(p))}</loc>"
        f"<lastmod>{p.updated_at.date().isoformat()}</lastmod></url>"
        for p in posts
    )

    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</urlset>'
    return Response(content=xml, media_type="application/xml")
