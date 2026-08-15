"""Noticias y recursos: albergues, jornadas, consejos y bienestar animal."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from .. import news_feed
from ..db import get_db
from ..models import ARTICLE_CATEGORIES, NEWS_TONE_LABELS, NEWS_TONES, Article
from ..schemas import ArticleOut, NewsListOut
from ..utils import category_label

router = APIRouter(prefix="/api/articles", tags=["noticias"])

# Actualidad: notas de medios externas, en su propio prefijo para no mezclarse
# con los artículos propios.
feed_router = APIRouter(prefix="/api/news", tags=["actualidad"])


@feed_router.get("/tones")
def news_tones() -> list[dict]:
    return [{"value": t, "label": NEWS_TONE_LABELS[t]} for t in NEWS_TONES]


@feed_router.get("/regions")
def news_regions() -> list[dict]:
    """Solo los departamentos afectados: filtrar por otros no daría resultados."""
    return [
        {"value": nombre, "label": nombre, "capital": municipios[1]}
        for nombre, municipios in news_feed.DEPARTAMENTOS.items()
    ]


@feed_router.get("", response_model=NewsListOut)
def news_feed_list(
    db: Session = Depends(get_db),
    tone: str | None = None,
    region: str | None = None,
    only_pets: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=24),
):
    if tone and tone not in NEWS_TONES:
        raise HTTPException(status_code=400, detail="Tono no válido.")
    if region and region not in news_feed.DEPARTAMENTOS:
        raise HTTPException(status_code=400, detail="Departamento no válido.")
    return news_feed.listar(
        db, tone=tone, region=region, only_pets=only_pets, page=page, page_size=page_size
    )


@router.get("/categories")
def categories() -> list[dict]:
    return [{"value": c, "label": category_label(c)} for c in ARTICLE_CATEGORIES]


@router.get("", response_model=list[ArticleOut])
def list_articles(
    db: Session = Depends(get_db),
    category: str | None = None,
    city: str | None = None,
    q: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
) -> list[Article]:
    filters = [Article.is_published.is_(True)]
    if category:
        filters.append(Article.category == category)
    if city:
        # Los recursos sin ciudad se consideran de alcance nacional.
        filters.append(or_(func.lower(Article.city) == city.lower(), Article.city.is_(None)))
    if q:
        needle = f"%{q.strip()}%"
        filters.append(or_(Article.title.ilike(needle), Article.content.ilike(needle)))

    return list(
        db.scalars(
            select(Article)
            .where(and_(*filters))
            .order_by(Article.published_at.desc())
            .limit(limit)
        ).all()
    )


@router.get("/{slug}", response_model=ArticleOut)
def get_article(slug: str, db: Session = Depends(get_db)) -> Article:
    article = db.scalar(select(Article).where(Article.slug == slug, Article.is_published.is_(True)))
    if not article:
        raise HTTPException(status_code=404, detail="No encontramos este contenido.")
    return article
