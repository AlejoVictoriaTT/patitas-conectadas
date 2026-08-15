"""Utilidades compartidas: slugs, teléfonos, antispam y etiquetas legibles."""

from __future__ import annotations

import re
import secrets
import time
import unicodedata

import httpx

from .config import settings
from .models import (
    ARTICLE_CATEGORY_LABELS,
    STATUS_ADOPTION_ACTIVE,
    STATUS_ADOPTION_DONE,
    STATUS_CLOSED,
    STATUS_FOUND_ACTIVE,
    STATUS_FOUND_DELIVERED,
    STATUS_LOST_ACTIVE,
    STATUS_LOST_REUNITED,
    TYPE_ADOPTION,
    TYPE_FOUND,
    TYPE_LOST,
)

_ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"  # sin caracteres ambiguos


def slugify(value: str, max_length: int = 60) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return ascii_text[:max_length].strip("-")


def generate_public_id(length: int = 8) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def normalize_phone(value: str | None, default_country_code: str = "57") -> str | None:
    """Deja el número en formato internacional sin signos, apto para wa.me."""
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    # Número colombiano de 10 dígitos sin indicativo
    if len(digits) == 10 and digits.startswith("3"):
        digits = default_country_code + digits
    return digits[:15]


def whatsapp_link(phone: str | None, message: str = "") -> str | None:
    number = normalize_phone(phone)
    if not number:
        return None
    from urllib.parse import quote

    base = f"https://wa.me/{number}"
    return f"{base}?text={quote(message)}" if message else base


# --------------------------------------------------------------- etiquetas UI

# Las etiquetas concuerdan en género con la mascota: un perro está «perdido» y
# una gata está «perdida». Las tablas en femenino son las genéricas (las que ven
# los formularios, donde todavía no hay una mascota concreta) y las `_M` son la
# variante masculina que se usa cuando la publicación sí tiene sexo y especie.

TYPE_LABELS = {
    TYPE_LOST: "Perdida",
    TYPE_FOUND: "Encontrada",
    TYPE_ADOPTION: "En adopción",
}

TYPE_LABELS_M = {
    TYPE_LOST: "Perdido",
    TYPE_FOUND: "Encontrado",
    TYPE_ADOPTION: "En adopción",
}

STATUS_LABELS = {
    STATUS_LOST_ACTIVE: "Perdida",
    STATUS_LOST_REUNITED: "Reunida con su familia",
    STATUS_FOUND_ACTIVE: "Encontrada — buscando a su familia",
    STATUS_FOUND_DELIVERED: "Entregada a su familia",
    STATUS_ADOPTION_ACTIVE: "Disponible para adopción",
    STATUS_ADOPTION_DONE: "Adoptada",
    STATUS_CLOSED: "Caso cerrado",
}

STATUS_LABELS_M = {
    STATUS_LOST_ACTIVE: "Perdido",
    STATUS_LOST_REUNITED: "Reunido con su familia",
    STATUS_FOUND_ACTIVE: "Encontrado — buscando a su familia",
    STATUS_FOUND_DELIVERED: "Entregado a su familia",
    STATUS_ADOPTION_ACTIVE: "Disponible para adopción",
    STATUS_ADOPTION_DONE: "Adoptado",
    STATUS_CLOSED: "Caso cerrado",
}

SPECIES_LABELS = {
    "perro": "Perro",
    "gato": "Gato",
    "otro": "Otro",
}

# Sustantivo con el que se nombra a la mascota cuando no tiene nombre propio.
PET_NOUNS = {
    ("perro", "macho"): "Perro",
    ("perro", "hembra"): "Perra",
    ("gato", "macho"): "Gato",
    ("gato", "hembra"): "Gata",
}

# Sin especie reconocida se usa «Mascota», que es femenino.
FALLBACK_NOUN = "Mascota"


def pet_gender(species: str | None, sex: str | None) -> str:
    """Devuelve 'm' o 'f': el género del sustantivo que nombra a la mascota.

    Sin sexo registrado se asume el masculino («Perro perdido»), que es la forma
    no marcada en español. Para especie «otro» siempre es femenino porque el
    sustantivo pasa a ser «Mascota».
    """
    if (species or "").lower() in ("perro", "gato"):
        return "f" if (sex or "").lower() == "hembra" else "m"
    return "f"


def pet_noun(species: str | None, sex: str | None) -> str:
    especie = (species or "").lower()
    if especie in ("perro", "gato"):
        return PET_NOUNS[(especie, "hembra" if (sex or "").lower() == "hembra" else "macho")]
    return FALLBACK_NOUN


def type_label(value: str, gender: str = "f") -> str:
    tabla = TYPE_LABELS_M if gender == "m" else TYPE_LABELS
    return tabla.get(value, value)


def status_label(value: str, gender: str = "f") -> str:
    tabla = STATUS_LABELS_M if gender == "m" else STATUS_LABELS
    return tabla.get(value, value)


def species_label(value: str) -> str:
    return SPECIES_LABELS.get(value, (value or "").capitalize())


def post_title(post) -> str:
    """Título visible: el nombre propio, o «Perra perdida» / «Gato encontrado»."""
    if post.pet_name:
        return post.pet_name
    genero = pet_gender(post.species, post.sex)
    return f"{pet_noun(post.species, post.sex)} {type_label(post.type, genero).lower()}"


def category_label(value: str) -> str:
    """Etiqueta con tildes de una categoría de «Noticias y ayuda»."""
    return ARTICLE_CATEGORY_LABELS.get(value, (value or "").replace("_", " ").capitalize())


# ------------------------------------------------------------------- antispam

_rate_buckets: dict[str, list[float]] = {}


def rate_limit_ok(key: str, limit: int, window_seconds: int) -> bool:
    """Límite de peticiones en memoria.

    En serverless cada instancia tiene su propio contador, así que es una barrera
    contra abuso trivial, no una garantía. El captcha opcional cubre el resto.
    """
    now = time.time()
    hits = [t for t in _rate_buckets.get(key, []) if now - t < window_seconds]
    if len(hits) >= limit:
        _rate_buckets[key] = hits
        return False
    hits.append(now)
    _rate_buckets[key] = hits
    return True


async def verify_captcha(token: str | None, remote_ip: str | None = None) -> bool:
    """Valida un token de Cloudflare Turnstile. Sin secreto configurado, no exige captcha."""
    if not settings.turnstile_secret:
        return True
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": settings.turnstile_secret,
                    "response": token,
                    **({"remoteip": remote_ip} if remote_ip else {}),
                },
            )
        return bool(response.json().get("success"))
    except httpx.HTTPError:
        # Ante un fallo del proveedor no bloqueamos publicaciones legítimas.
        return True


def client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "desconocido"
