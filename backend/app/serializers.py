"""Conversión de modelos a las respuestas públicas de la API.

Regla de privacidad: la dirección exacta y los datos de contacto completos solo
se devuelven a quien administra la publicación o al panel de administración.
"""

from __future__ import annotations

from .config import settings
from .models import Post
from .utils import (
    pet_gender,
    pet_noun,
    post_title,
    species_label,
    status_label,
    type_label,
    whatsapp_link,
)

WHATSAPP_TEMPLATE = (
    "Hola, vi la publicación de {mascota} en {plataforma} y quisiera obtener más información."
)


def post_path(post: Post) -> str:
    return f"/mascotas/{post.type}/{post.slug}"


def post_url(post: Post) -> str:
    return f"{settings.site_url}{post_path(post)}"


def _pet_reference(post: Post) -> str:
    if post.pet_name:
        return f"{post.pet_name} ({pet_noun(post.species, post.sex).lower()})"
    articulo = "una" if pet_gender(post.species, post.sex) == "f" else "un"
    return f"{articulo} {pet_noun(post.species, post.sex).lower()} en {post.city}"


def build_whatsapp_link(post: Post) -> str | None:
    message = WHATSAPP_TEMPLATE.format(mascota=_pet_reference(post), plataforma=settings.app_name)
    return whatsapp_link(post.contact_whatsapp, message)


def photo_to_dict(photo) -> dict:
    return {
        "id": photo.id,
        "url": photo.url,
        "position": photo.position,
        "is_primary": photo.is_primary,
    }


def post_to_card(post: Post) -> dict:
    primary = post.primary_photo
    # Las etiquetas concuerdan con la mascota, así que se calculan aquí una sola
    # vez y el frontend las muestra tal cual (evita «Perro perdida»).
    gender = pet_gender(post.species, post.sex)
    return {
        "id": post.id,
        "public_id": post.public_id,
        "slug": post.slug,
        "url": post_path(post),
        "title": post_title(post),
        "gender": gender,
        "type": post.type,
        "type_label": type_label(post.type, gender),
        "status": post.status,
        "status_label": status_label(post.status, gender),
        "species": post.species,
        "species_label": species_label(post.species),
        "sex": post.sex,
        "pet_name": post.pet_name,
        "city": post.city,
        "region": post.region,
        "neighborhood": post.neighborhood,
        "event_date": post.event_date,
        "created_at": post.created_at,
        "photo_url": primary.url if primary else None,
        "is_resolved": post.is_resolved,
    }


def post_to_detail(post: Post, *, is_owner: bool = False, manage_token: str | None = None) -> dict:
    data = post_to_card(post)
    data.update(
        {
            "breed": post.breed,
            "age": post.age,
            "color": post.color,
            "size": post.size,
            "has_collar": post.has_collar,
            "has_tag": post.has_tag,
            "special_marks": post.special_marks,
            "description": post.description,
            "location": {
                "country": post.country,
                "region": post.region,
                "city": post.city,
                "neighborhood": post.neighborhood,
                # La dirección exacta nunca es pública.
                "address": post.address if is_owner else None,
            },
            "contact": {
                "name": post.contact_name,
                "whatsapp": post.contact_whatsapp,
                "phone": post.contact_phone,
                "email": post.contact_email,
                "note": post.contact_note,
                "whatsapp_link": build_whatsapp_link(post),
            },
            "photos": [photo_to_dict(p) for p in sorted(post.photos, key=lambda p: p.position)],
            "views": post.views,
            "is_active": post.is_active,
            "is_owner": is_owner,
            "owner_name": post.owner.name if post.owner else post.contact_name,
            "has_account_owner": bool(post.user_id),
            "manage_token": manage_token,
        }
    )
    return data
