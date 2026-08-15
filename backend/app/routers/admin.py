"""Panel administrativo básico: publicaciones, reportes, usuarios, contenido y métricas."""

from __future__ import annotations

import math
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select, true
from sqlalchemy.orm import Session, selectinload

from .. import news_feed
from ..db import get_db
from ..models import (
    NEWS_TONE_LABELS,
    RESOLVED_STATUSES,
    TYPE_ADOPTION,
    TYPE_FOUND,
    TYPE_LOST,
    Article,
    NewsItem,
    Post,
    Report,
    User,
    utcnow,
)
from ..schemas import (
    AdminPostFlagIn,
    AdminReportUpdateIn,
    AdminStatsOut,
    AdminUserUpdateIn,
    ArticleIn,
    ArticleOut,
    PostListOut,
    UserOut,
)
from ..security import get_current_admin
from ..serializers import post_path, post_to_card
from ..utils import generate_public_id, post_title, slugify
from .visits import resumen_visitas

router = APIRouter(prefix="/api/admin", tags=["administración"], dependencies=[Depends(get_current_admin)])


# ------------------------------------------------------------------ estadísticas


@router.get("/stats", response_model=AdminStatsOut)
def stats(db: Session = Depends(get_db)) -> AdminStatsOut:
    def count_posts(*conditions) -> int:
        return db.scalar(select(func.count()).select_from(Post).where(*conditions)) or 0

    week_ago = utcnow() - timedelta(days=7)
    top_cities = db.execute(
        select(Post.city, func.count(Post.id).label("total"))
        .group_by(Post.city)
        .order_by(func.count(Post.id).desc())
        .limit(8)
    ).all()

    # Publicaciones más vistas: sirve para saber qué está atrayendo tráfico.
    mas_vistas = db.scalars(
        select(Post).where(Post.views > 0).order_by(Post.views.desc()).limit(8)
    ).all()

    return AdminStatsOut(
        total_posts=count_posts(),
        active_posts=count_posts(Post.is_active.is_(True), Post.status.notin_(RESOLVED_STATUSES)),
        lost=count_posts(Post.type == TYPE_LOST),
        found=count_posts(Post.type == TYPE_FOUND),
        adoption=count_posts(Post.type == TYPE_ADOPTION),
        resolved=count_posts(Post.status.in_(RESOLVED_STATUSES)),
        pending_reports=db.scalar(
            select(func.count()).select_from(Report).where(Report.status == "pendiente")
        ) or 0,
        users=db.scalar(select(func.count()).select_from(User)) or 0,
        posts_last_7_days=count_posts(Post.created_at >= week_ago),
        top_cities=[{"city": row.city, "total": row.total} for row in top_cities],
        visits=resumen_visitas(db),
        total_post_views=int(db.scalar(select(func.coalesce(func.sum(Post.views), 0))) or 0),
        most_viewed=[
            {
                "id": p.id,
                "title": post_title(p),
                "city": p.city,
                "url": post_path(p),
                "views": p.views,
            }
            for p in mas_vistas
        ],
    )


# ----------------------------------------------------------------- publicaciones


@router.get("/posts")
def admin_list_posts(
    db: Session = Depends(get_db),
    q: str | None = None,
    city: str | None = None,
    type: str | None = None,
    status_: str | None = Query(default=None, alias="status"),
    only_hidden: bool = False,
    only_reported: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    filters = []
    if q:
        needle = f"%{q.strip()}%"
        filters.append(
            or_(
                Post.pet_name.ilike(needle),
                Post.description.ilike(needle),
                Post.contact_email.ilike(needle),
                Post.public_id.ilike(needle),
            )
        )
    if city:
        filters.append(func.lower(Post.city) == city.lower())
    if type:
        filters.append(Post.type == type)
    if status_:
        filters.append(Post.status == status_)
    if only_hidden:
        filters.append(Post.is_active.is_(False))
    if only_reported:
        filters.append(Post.reports_count > 0)

    where = and_(*filters) if filters else true()
    total = db.scalar(select(func.count()).select_from(Post).where(where)) or 0
    rows = db.scalars(
        select(Post)
        .options(selectinload(Post.photos))
        .where(where)
        .order_by(Post.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = []
    for post in rows:
        card = post_to_card(post)
        card.update(
            {
                "is_active": post.is_active,
                "reports_count": post.reports_count,
                "views": post.views,
                "hidden_reason": post.hidden_reason,
                "contact_email": post.contact_email,
            }
        )
        items.append(card)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
    }


@router.post("/posts/{post_id}/visibility")
def set_post_visibility(post_id: str, payload: AdminPostFlagIn, db: Session = Depends(get_db)) -> dict:
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Publicación no encontrada.")
    post.is_active = payload.is_active
    post.hidden_reason = None if payload.is_active else (payload.hidden_reason or "Desactivada por moderación.")
    db.commit()
    return {"ok": True, "is_active": post.is_active}


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def admin_delete_post(post_id: str, db: Session = Depends(get_db)) -> None:
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Publicación no encontrada.")
    db.delete(post)
    db.commit()


# ---------------------------------------------------------------------- reportes


@router.get("/reports")
def admin_list_reports(
    db: Session = Depends(get_db),
    status_: str | None = Query(default="pendiente", alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    query = select(Report).options(selectinload(Report.post)).order_by(Report.created_at.desc()).limit(limit)
    if status_:
        query = query.where(Report.status == status_)

    result = []
    for report in db.scalars(query).all():
        post = report.post
        result.append(
            {
                "id": report.id,
                "reason": report.reason,
                "details": report.details,
                "status": report.status,
                "created_at": report.created_at,
                "admin_note": report.admin_note,
                "post": {
                    "id": post.id,
                    "slug": post.slug,
                    "type": post.type,
                    "pet_name": post.pet_name,
                    "city": post.city,
                    "is_active": post.is_active,
                    "reports_count": post.reports_count,
                }
                if post
                else None,
            }
        )
    return result


@router.patch("/reports/{report_id}")
def admin_update_report(report_id: str, payload: AdminReportUpdateIn, db: Session = Depends(get_db)) -> dict:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado.")

    report.status = payload.status
    report.admin_note = payload.admin_note
    report.reviewed_at = utcnow()

    if payload.hide_post and report.post:
        report.post.is_active = False
        report.post.hidden_reason = payload.admin_note or "Desactivada tras revisión de un reporte."

    db.commit()
    return {"ok": True, "status": report.status}


# ---------------------------------------------------------------------- usuarios


@router.get("/users", response_model=list[UserOut])
def admin_list_users(
    db: Session = Depends(get_db),
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[User]:
    query = select(User).order_by(User.created_at.desc()).limit(limit)
    if q:
        needle = f"%{q.strip()}%"
        query = query.where(or_(User.name.ilike(needle), User.email.ilike(needle)))
    return list(db.scalars(query).all())


@router.patch("/users/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: str,
    payload: AdminUserUpdateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if user.id == admin.id and payload.is_admin is False:
        raise HTTPException(status_code=400, detail="No puedes quitarte a ti mismo el rol de administrador.")

    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    db.commit()
    db.refresh(user)
    return user


# -------------------------------------------------------------- noticias/recursos


# ------------------------------------------------------------------ actualidad


@router.post("/news/sync")
async def admin_sync_news(db: Session = Depends(get_db)) -> dict:
    """Dispara la ingesta a mano, sin esperar al cron diario."""
    return {"ok": True, **await news_feed.sincronizar(db)}


@router.get("/news")
def admin_list_news(db: Session = Depends(get_db), limit: int = Query(default=40, ge=1, le=100)) -> list[dict]:
    filas = db.scalars(
        select(NewsItem).order_by(NewsItem.published_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "source": n.source,
            "tone": n.tone,
            "tone_label": NEWS_TONE_LABELS.get(n.tone, n.tone),
            "url": n.url,
            "cities": n.cities,
            "is_pet_related": n.is_pet_related,
            "is_published": n.is_published,
            "published_at": n.published_at,
        }
        for n in filas
    ]


@router.post("/news/{item_id}/visibility")
def admin_news_visibility(item_id: str, payload: AdminPostFlagIn, db: Session = Depends(get_db)) -> dict:
    item = db.get(NewsItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Noticia no encontrada.")
    item.is_published = payload.is_active
    db.commit()
    return {"ok": True, "is_published": item.is_published}


@router.get("/articles", response_model=list[ArticleOut])
def admin_list_articles(db: Session = Depends(get_db)) -> list[Article]:
    return list(db.scalars(select(Article).order_by(Article.published_at.desc())).all())


def _unique_slug(db: Session, title: str, current_id: str | None = None) -> str:
    base = slugify(title) or "contenido"
    slug = base
    while True:
        existing = db.scalar(select(Article).where(Article.slug == slug))
        if not existing or existing.id == current_id:
            return slug
        slug = f"{base}-{generate_public_id(4)}"


@router.post("/articles", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
def admin_create_article(payload: ArticleIn, db: Session = Depends(get_db)) -> Article:
    article = Article(**payload.model_dump(), slug=_unique_slug(db, payload.title))
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@router.put("/articles/{article_id}", response_model=ArticleOut)
def admin_update_article(article_id: str, payload: ArticleIn, db: Session = Depends(get_db)) -> Article:
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Contenido no encontrado.")

    for field, value in payload.model_dump().items():
        setattr(article, field, value)
    article.slug = _unique_slug(db, payload.title, current_id=article.id)

    db.commit()
    db.refresh(article)
    return article


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def admin_delete_article(article_id: str, db: Session = Depends(get_db)) -> None:
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Contenido no encontrado.")
    db.delete(article)
    db.commit()
