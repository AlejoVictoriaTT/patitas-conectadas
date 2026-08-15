"""Publicaciones de mascotas: creación, búsqueda, detalle, estados y fotos."""

from __future__ import annotations

import math
from datetime import date

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import notify
from ..config import settings
from ..db import get_db
from ..models import (
    ALLOWED_STATUSES,
    INITIAL_STATUS,
    RESOLVED_STATUSES,
    Photo,
    Post,
    User,
    utcnow,
)
from ..schemas import (
    PhotoIn,
    PhotoReorderIn,
    PostCreatedOut,
    PostCreateIn,
    PostDetailOut,
    PostListOut,
    PostUpdateIn,
    StatusUpdateIn,
)
from ..security import (
    generate_manage_token,
    get_current_user,
    get_current_user_optional,
    hash_manage_token,
    manage_token_matches,
)
from ..serializers import post_to_card, post_to_detail, post_url
from ..storage import delete_image
from ..utils import client_ip, generate_public_id, normalize_phone, rate_limit_ok, slugify, species_label, verify_captcha

router = APIRouter(prefix="/api", tags=["publicaciones"])

MAX_PAGE_SIZE = 48


# --------------------------------------------------------------------- helpers


def _load_post(db: Session, identifier: str) -> Post:
    """Busca por slug, public_id o id."""
    query = select(Post).options(selectinload(Post.photos), selectinload(Post.owner)).where(
        or_(Post.slug == identifier, Post.public_id == identifier, Post.id == identifier)
    )
    post = db.scalar(query)
    if not post:
        raise HTTPException(status_code=404, detail="No encontramos esta publicación.")
    return post


def _is_owner(post: Post, user: User | None, manage_token: str | None) -> bool:
    if user and (user.is_admin or (post.user_id and post.user_id == user.id)):
        return True
    if manage_token and manage_token_matches(manage_token, post.manage_token_hash):
        return True
    return False


def _require_owner(post: Post, user: User | None, manage_token: str | None) -> None:
    if not _is_owner(post, user, manage_token):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para administrar esta publicación.",
        )


def _build_slug(db: Session, payload_name: str | None, species: str, post_type: str, public_id: str) -> str:
    base = slugify(payload_name or f"{species_label(species)}-{post_type}") or "mascota"
    slug = f"{base}-{public_id}"
    while db.scalar(select(func.count()).select_from(Post).where(Post.slug == slug)):
        slug = f"{base}-{generate_public_id(4)}"
    return slug


def _validate_photo_urls(photos: list[PhotoIn]) -> None:
    for photo in photos:
        if not (photo.url.startswith("/uploads/") or photo.url.startswith("https://")):
            raise HTTPException(status_code=400, detail="Una de las fotos no es válida. Vuelve a subirla.")


def _apply_photos(post: Post, photos: list[PhotoIn]) -> None:
    primary_seen = False
    for index, item in enumerate(photos):
        is_primary = item.is_primary and not primary_seen
        primary_seen = primary_seen or is_primary
        post.photos.append(Photo(url=item.url, position=index, is_primary=is_primary))
    if not primary_seen and post.photos:
        post.photos[0].is_primary = True


def _renumber_photos(post: Post) -> None:
    ordered = sorted(post.photos, key=lambda p: p.position)
    for index, photo in enumerate(ordered):
        photo.position = index
    if ordered and not any(p.is_primary for p in ordered):
        ordered[0].is_primary = True


# ------------------------------------------------------------------- listados


@router.get("/posts", response_model=PostListOut)
def list_posts(
    db: Session = Depends(get_db),
    type: str | None = Query(default=None, description="perdida | encontrada | adopcion"),
    species: str | None = None,
    status_: str | None = Query(default=None, alias="status"),
    country: str | None = None,
    region: str | None = None,
    city: str | None = None,
    sex: str | None = None,
    breed: str | None = None,
    color: str | None = None,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_resolved: bool = Query(default=False, description="Incluir casos ya resueltos o cerrados"),
    sort: str = Query(default="recientes", description="recientes | evento | antiguas"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=MAX_PAGE_SIZE),
) -> PostListOut:
    filters = [Post.is_active.is_(True)]

    if type:
        filters.append(Post.type == type)
    if species:
        filters.append(Post.species == species)
    if status_:
        filters.append(Post.status == status_)
    elif not include_resolved:
        filters.append(Post.status.notin_(RESOLVED_STATUSES))
    if country:
        filters.append(Post.country == country)
    if region:
        filters.append(Post.region == region)
    if city:
        filters.append(func.lower(Post.city) == city.lower())
    if sex:
        filters.append(Post.sex == sex)
    if breed:
        filters.append(Post.breed.ilike(f"%{breed}%"))
    if color:
        filters.append(Post.color.ilike(f"%{color}%"))
    if date_from:
        filters.append(Post.event_date >= date_from)
    if date_to:
        filters.append(Post.event_date <= date_to)
    if q:
        needle = f"%{q.strip()}%"
        filters.append(
            or_(
                Post.pet_name.ilike(needle),
                Post.description.ilike(needle),
                Post.breed.ilike(needle),
                Post.color.ilike(needle),
                Post.city.ilike(needle),
                Post.neighborhood.ilike(needle),
            )
        )

    where = and_(*filters)
    total = db.scalar(select(func.count()).select_from(Post).where(where)) or 0

    order = {
        "recientes": Post.created_at.desc(),
        "antiguas": Post.created_at.asc(),
        "evento": Post.event_date.desc(),
    }.get(sort, Post.created_at.desc())

    rows = db.scalars(
        select(Post)
        .options(selectinload(Post.photos))
        .where(where)
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return PostListOut(
        items=[post_to_card(p) for p in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/posts/cities")
def cities_with_posts(db: Session = Depends(get_db), limit: int = Query(default=40, ge=1, le=200)) -> list[dict]:
    """Ciudades que ya tienen publicaciones activas (para el selector de la portada)."""
    rows = db.execute(
        select(Post.city, Post.region, Post.country, func.count(Post.id).label("total"))
        .where(Post.is_active.is_(True), Post.status.notin_(RESOLVED_STATUSES))
        .group_by(Post.city, Post.region, Post.country)
        .order_by(func.count(Post.id).desc())
        .limit(limit)
    ).all()
    return [{"city": r.city, "region": r.region, "country": r.country, "total": r.total} for r in rows]


@router.get("/posts/mine", response_model=list[dict])
def my_posts(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(Post)
        .options(selectinload(Post.photos))
        .where(Post.user_id == user.id)
        .order_by(Post.created_at.desc())
    ).all()
    return [{**post_to_card(p), "is_active": p.is_active, "views": p.views} for p in rows]


# -------------------------------------------------------------------- creación


@router.post("/posts", response_model=PostCreatedOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreateIn,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> PostCreatedOut:
    ip = client_ip(request)

    # Antispam: honeypot invisible + límite por IP + captcha opcional
    if payload.website:
        raise HTTPException(status_code=400, detail="No pudimos validar el formulario.")
    if not rate_limit_ok(f"post:{ip}", limit=6, window_seconds=3600):
        raise HTTPException(
            status_code=429,
            detail="Has publicado varias veces en poco tiempo. Intenta de nuevo más tarde.",
        )
    if not await verify_captcha(payload.captcha_token, ip):
        raise HTTPException(status_code=400, detail="Verificación de seguridad fallida. Inténtalo otra vez.")

    _validate_photo_urls(payload.photos)

    public_id = generate_public_id()
    while db.scalar(select(func.count()).select_from(Post).where(Post.public_id == public_id)):
        public_id = generate_public_id()

    post = Post(
        public_id=public_id,
        slug=_build_slug(db, payload.pet_name, payload.species, payload.type, public_id),
        type=payload.type,
        status=INITIAL_STATUS[payload.type],
        species=payload.species,
        pet_name=(payload.pet_name or "").strip() or None,
        breed=(payload.breed or "").strip() or None,
        sex=payload.sex,
        age=(payload.age or "").strip() or None,
        color=(payload.color or "").strip() or None,
        size=payload.size,
        has_collar=payload.has_collar,
        has_tag=payload.has_tag,
        special_marks=(payload.special_marks or "").strip() or None,
        description=payload.description.strip(),
        country=payload.location.country.strip(),
        region=(payload.location.region or "").strip() or None,
        city=payload.location.city.strip(),
        neighborhood=(payload.location.neighborhood or "").strip() or None,
        address=(payload.location.address or "").strip() or None,
        event_date=payload.event_date,
        contact_name=(payload.contact.name or "").strip() or (user.name if user else None),
        contact_whatsapp=normalize_phone(payload.contact.whatsapp),
        contact_phone=normalize_phone(payload.contact.phone),
        contact_email=payload.contact.email,
        contact_note=(payload.contact.note or "").strip() or None,
        user_id=user.id if user else None,
    )

    manage_token: str | None = None
    if user is None:
        manage_token = generate_manage_token()
        post.manage_token_hash = hash_manage_token(manage_token)
        post.guest_email = payload.guest_email or payload.contact.email

    _apply_photos(post, payload.photos)

    db.add(post)
    db.commit()
    db.refresh(post)

    # Alerta al administrador. El mensaje se arma aquí, con la sesión abierta, y
    # el envío se agenda para después de responder: si el proveedor está caído o
    # tarda, la persona que publicó no se entera ni espera.
    if notify.esta_activo():
        background_tasks.add_task(notify.enviar, notify.construir_mensaje(post))

    detail = post_to_detail(post, is_owner=True, manage_token=manage_token)
    return PostCreatedOut(
        post=PostDetailOut(**detail),
        manage_token=manage_token,
        manage_url=f"{settings.site_url}/gestionar/{manage_token}" if manage_token else None,
        share_url=post_url(post),
    )


# ---------------------------------------------------------------------- detalle


@router.get("/posts/{identifier}", response_model=PostDetailOut)
def get_post(
    identifier: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
    x_manage_token: str | None = Header(default=None),
) -> PostDetailOut:
    post = _load_post(db, identifier)
    owner = _is_owner(post, user, x_manage_token)

    if not post.is_active and not owner:
        raise HTTPException(status_code=404, detail="Esta publicación no está disponible.")

    post.views += 1
    db.commit()
    db.refresh(post)

    return PostDetailOut(**post_to_detail(post, is_owner=owner))


@router.get("/manage/{manage_token}", response_model=PostDetailOut)
def get_post_by_manage_token(manage_token: str, db: Session = Depends(get_db)) -> PostDetailOut:
    """Acceso de un usuario invitado a su publicación mediante enlace privado."""
    post = db.scalar(
        select(Post)
        .options(selectinload(Post.photos), selectinload(Post.owner))
        .where(Post.manage_token_hash == hash_manage_token(manage_token))
    )
    if not post:
        raise HTTPException(status_code=404, detail="El enlace de administración no es válido o expiró.")
    return PostDetailOut(**post_to_detail(post, is_owner=True, manage_token=manage_token))


# ----------------------------------------------------------------- edición


@router.patch("/posts/{identifier}", response_model=PostDetailOut)
def update_post(
    identifier: str,
    payload: PostUpdateIn,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
    x_manage_token: str | None = Header(default=None),
) -> PostDetailOut:
    post = _load_post(db, identifier)
    _require_owner(post, user, x_manage_token)

    data = payload.model_dump(exclude_unset=True)

    location = data.pop("location", None)
    if location:
        post.country = (location.get("country") or post.country).strip()
        post.region = (location.get("region") or "").strip() or None
        post.city = (location.get("city") or post.city).strip()
        post.neighborhood = (location.get("neighborhood") or "").strip() or None
        post.address = (location.get("address") or "").strip() or None

    contact = data.pop("contact", None)
    if contact:
        post.contact_name = (contact.get("name") or "").strip() or None
        post.contact_whatsapp = normalize_phone(contact.get("whatsapp"))
        post.contact_phone = normalize_phone(contact.get("phone"))
        post.contact_email = contact.get("email")
        post.contact_note = (contact.get("note") or "").strip() or None

    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(post, field, value)

    if "pet_name" in data:
        post.slug = _build_slug(db, post.pet_name, post.species, post.type, post.public_id)

    db.commit()
    db.refresh(post)
    return PostDetailOut(**post_to_detail(post, is_owner=True, manage_token=x_manage_token))


@router.post("/posts/{identifier}/status", response_model=PostDetailOut)
def change_status(
    identifier: str,
    payload: StatusUpdateIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
    x_manage_token: str | None = Header(default=None),
) -> PostDetailOut:
    post = _load_post(db, identifier)
    _require_owner(post, user, x_manage_token)

    allowed = ALLOWED_STATUSES[post.type]
    if payload.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Estado no válido para este tipo de publicación. Opciones: {', '.join(allowed)}",
        )

    estado_anterior = post.status
    post.status = payload.status
    post.resolved_at = utcnow() if payload.status in RESOLVED_STATUSES else None
    db.commit()
    db.refresh(post)

    # Solo se avisa si el estado cambió de verdad: guardar el mismo valor dos
    # veces no es una noticia. El mensaje se arma aquí, con la sesión abierta.
    if estado_anterior != post.status and notify.esta_activo():
        background_tasks.add_task(
            notify.enviar, notify.construir_mensaje_estado(post, estado_anterior)
        )

    return PostDetailOut(**post_to_detail(post, is_owner=True, manage_token=x_manage_token))


@router.delete("/posts/{identifier}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_post(
    identifier: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
    x_manage_token: str | None = Header(default=None),
) -> None:
    post = _load_post(db, identifier)
    _require_owner(post, user, x_manage_token)

    urls = [photo.url for photo in post.photos]
    db.delete(post)
    db.commit()
    for url in urls:
        await delete_image(url)


# ------------------------------------------------------------------- fotos


@router.post("/posts/{identifier}/photos", response_model=PostDetailOut)
def add_photos(
    identifier: str,
    photos: list[PhotoIn],
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
    x_manage_token: str | None = Header(default=None),
) -> PostDetailOut:
    post = _load_post(db, identifier)
    _require_owner(post, user, x_manage_token)
    _validate_photo_urls(photos)

    if len(post.photos) + len(photos) > settings.max_photos:
        raise HTTPException(
            status_code=400,
            detail=f"Puedes tener máximo {settings.max_photos} fotos por publicación.",
        )

    start = len(post.photos)
    for offset, item in enumerate(photos):
        post.photos.append(Photo(url=item.url, position=start + offset, is_primary=False))
    _renumber_photos(post)

    db.commit()
    db.refresh(post)
    return PostDetailOut(**post_to_detail(post, is_owner=True, manage_token=x_manage_token))


@router.delete("/posts/{identifier}/photos/{photo_id}", response_model=PostDetailOut)
async def delete_photo(
    identifier: str,
    photo_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
    x_manage_token: str | None = Header(default=None),
) -> PostDetailOut:
    post = _load_post(db, identifier)
    _require_owner(post, user, x_manage_token)

    if len(post.photos) <= 1:
        raise HTTPException(
            status_code=400,
            detail="La publicación debe conservar al menos una foto. Sube otra antes de eliminar esta.",
        )

    photo = next((p for p in post.photos if p.id == photo_id), None)
    if not photo:
        raise HTTPException(status_code=404, detail="Esa foto ya no existe.")

    url = photo.url
    was_primary = photo.is_primary
    post.photos.remove(photo)
    _renumber_photos(post)
    if was_primary and post.photos:
        for candidate in post.photos:
            candidate.is_primary = False
        sorted(post.photos, key=lambda p: p.position)[0].is_primary = True

    db.commit()
    db.refresh(post)
    await delete_image(url)
    return PostDetailOut(**post_to_detail(post, is_owner=True, manage_token=x_manage_token))


@router.post("/posts/{identifier}/photos/{photo_id}/primary", response_model=PostDetailOut)
def set_primary_photo(
    identifier: str,
    photo_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
    x_manage_token: str | None = Header(default=None),
) -> PostDetailOut:
    post = _load_post(db, identifier)
    _require_owner(post, user, x_manage_token)

    if not any(p.id == photo_id for p in post.photos):
        raise HTTPException(status_code=404, detail="Esa foto ya no existe.")

    for photo in post.photos:
        photo.is_primary = photo.id == photo_id

    db.commit()
    db.refresh(post)
    return PostDetailOut(**post_to_detail(post, is_owner=True, manage_token=x_manage_token))


@router.post("/posts/{identifier}/photos/reorder", response_model=PostDetailOut)
def reorder_photos(
    identifier: str,
    payload: PhotoReorderIn,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
    x_manage_token: str | None = Header(default=None),
) -> PostDetailOut:
    post = _load_post(db, identifier)
    _require_owner(post, user, x_manage_token)

    current = {photo.id: photo for photo in post.photos}
    if set(payload.photo_ids) != set(current):
        raise HTTPException(status_code=400, detail="La lista de fotos no coincide con la publicación.")

    for index, photo_id in enumerate(payload.photo_ids):
        current[photo_id].position = index

    db.commit()
    db.refresh(post)
    return PostDetailOut(**post_to_detail(post, is_owner=True, manage_token=x_manage_token))
