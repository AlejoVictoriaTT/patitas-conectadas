"""Esquemas de entrada y salida de la API (Pydantic v2)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .models import ARTICLE_CATEGORIES, POST_TYPES, REPORT_REASONS, SEXES, SIZES, SPECIES

PostTypeLiteral = Literal["perdida", "encontrada", "adopcion"]


# ------------------------------------------------------------------- usuarios


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    avatar_url: str | None = None
    phone: str | None = None
    is_admin: bool
    created_at: datetime


class RegisterIn(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=120)]
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProfileUpdateIn(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=120)] | None = None
    phone: Annotated[str, Field(max_length=30)] | None = None


class PasswordChangeIn(BaseModel):
    current_password: str | None = None
    new_password: Annotated[str, Field(min_length=8, max_length=128)]


# ------------------------------------------------------------------- fotos


class PhotoIn(BaseModel):
    url: Annotated[str, Field(min_length=5, max_length=600)]
    is_primary: bool = False


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    position: int
    is_primary: bool


class UploadOut(BaseModel):
    url: str


# ------------------------------------------------------------- publicaciones


class ContactIn(BaseModel):
    name: Annotated[str, Field(max_length=120)] | None = None
    whatsapp: Annotated[str, Field(max_length=30)] | None = None
    phone: Annotated[str, Field(max_length=30)] | None = None
    email: EmailStr | None = None
    note: Annotated[str, Field(max_length=500)] | None = None

    @model_validator(mode="after")
    def at_least_one_channel(self):
        if not any([self.whatsapp, self.phone, self.email]):
            raise ValueError("Agrega al menos un medio de contacto: WhatsApp, teléfono o correo.")
        return self


class LocationIn(BaseModel):
    country: Annotated[str, Field(min_length=2, max_length=60)] = "Colombia"
    region: Annotated[str, Field(max_length=80)] | None = None
    city: Annotated[str, Field(min_length=2, max_length=80)]
    neighborhood: Annotated[str, Field(max_length=120)] | None = None
    address: Annotated[str, Field(max_length=200)] | None = None


class PostCreateIn(BaseModel):
    type: PostTypeLiteral
    species: str
    description: Annotated[str, Field(min_length=10, max_length=2000)]
    event_date: date
    location: LocationIn
    contact: ContactIn
    photos: Annotated[list[PhotoIn], Field(min_length=1, max_length=5)]

    # Opcionales
    pet_name: Annotated[str, Field(max_length=80)] | None = None
    breed: Annotated[str, Field(max_length=80)] | None = None
    sex: str | None = None
    age: Annotated[str, Field(max_length=60)] | None = None
    color: Annotated[str, Field(max_length=80)] | None = None
    size: str | None = None
    has_collar: bool | None = None
    has_tag: bool | None = None
    special_marks: Annotated[str, Field(max_length=500)] | None = None

    # Invitados y antispam
    guest_email: EmailStr | None = None
    captcha_token: str | None = None
    website: str | None = None  # honeypot: debe llegar vacío

    @field_validator("species")
    @classmethod
    def valid_species(cls, value: str) -> str:
        if value not in SPECIES:
            raise ValueError(f"Especie no válida. Opciones: {', '.join(SPECIES)}")
        return value

    @field_validator("sex")
    @classmethod
    def valid_sex(cls, value: str | None) -> str | None:
        if value and value not in SEXES:
            raise ValueError(f"Sexo no válido. Opciones: {', '.join(SEXES)}")
        return value

    @field_validator("size")
    @classmethod
    def valid_size(cls, value: str | None) -> str | None:
        if value and value not in SIZES:
            raise ValueError(f"Tamaño no válido. Opciones: {', '.join(SIZES)}")
        return value

    @field_validator("event_date")
    @classmethod
    def not_in_future(cls, value: date) -> date:
        from datetime import timezone as _tz

        today = datetime.now(_tz.utc).date()
        if value > today:
            raise ValueError("La fecha no puede ser posterior a hoy.")
        if value.year < 2000:
            raise ValueError("La fecha no es válida.")
        return value

    @model_validator(mode="after")
    def single_primary_photo(self):
        primaries = [p for p in self.photos if p.is_primary]
        if len(primaries) > 1:
            raise ValueError("Solo puede haber una foto principal.")
        if not primaries:
            self.photos[0].is_primary = True
        return self


class PostUpdateIn(BaseModel):
    description: Annotated[str, Field(min_length=10, max_length=2000)] | None = None
    event_date: date | None = None
    location: LocationIn | None = None
    contact: ContactIn | None = None
    pet_name: Annotated[str, Field(max_length=80)] | None = None
    breed: Annotated[str, Field(max_length=80)] | None = None
    sex: str | None = None
    age: Annotated[str, Field(max_length=60)] | None = None
    color: Annotated[str, Field(max_length=80)] | None = None
    size: str | None = None
    has_collar: bool | None = None
    has_tag: bool | None = None
    special_marks: Annotated[str, Field(max_length=500)] | None = None
    species: str | None = None

    @field_validator("species")
    @classmethod
    def valid_species(cls, value: str | None) -> str | None:
        if value and value not in SPECIES:
            raise ValueError(f"Especie no válida. Opciones: {', '.join(SPECIES)}")
        return value


class StatusUpdateIn(BaseModel):
    status: Annotated[str, Field(min_length=3, max_length=30)]


class PhotoReorderIn(BaseModel):
    photo_ids: Annotated[list[str], Field(min_length=1, max_length=5)]


class ContactOut(BaseModel):
    name: str | None = None
    whatsapp: str | None = None
    phone: str | None = None
    email: str | None = None
    note: str | None = None
    whatsapp_link: str | None = None


class LocationOut(BaseModel):
    country: str
    region: str | None = None
    city: str
    neighborhood: str | None = None
    address: str | None = None  # solo se incluye para el propietario/administrador


class PostCardOut(BaseModel):
    """Versión ligera usada en listados y tarjetas."""

    id: str
    public_id: str
    slug: str
    url: str
    # Título ya concordado en género («Perra perdida», «Gato encontrado») y el
    # género con el que concuerdan las demás etiquetas: 'm' o 'f'.
    title: str
    gender: str
    type: PostTypeLiteral
    type_label: str
    status: str
    status_label: str
    species: str
    species_label: str
    sex: str | None
    pet_name: str | None
    city: str
    region: str | None
    neighborhood: str | None
    event_date: date
    created_at: datetime
    photo_url: str | None
    is_resolved: bool


class PostDetailOut(PostCardOut):
    breed: str | None
    age: str | None
    color: str | None
    size: str | None
    has_collar: bool | None
    has_tag: bool | None
    special_marks: str | None
    description: str
    location: LocationOut
    contact: ContactOut
    photos: list[PhotoOut]
    views: int
    is_active: bool
    is_owner: bool = False
    owner_name: str | None = None
    has_account_owner: bool = False
    manage_token: str | None = None


class PostListOut(BaseModel):
    items: list[PostCardOut]
    total: int
    page: int
    page_size: int
    pages: int


class PostCreatedOut(BaseModel):
    post: PostDetailOut
    manage_token: str | None = None
    manage_url: str | None = None
    share_url: str


# --------------------------------------------------------------------- reportes


class ReportIn(BaseModel):
    reason: str
    details: Annotated[str, Field(max_length=1000)] | None = None
    reporter_email: EmailStr | None = None
    captcha_token: str | None = None

    @field_validator("reason")
    @classmethod
    def valid_reason(cls, value: str) -> str:
        if value not in REPORT_REASONS:
            raise ValueError("Motivo de reporte no válido.")
        return value


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    post_id: str
    reason: str
    details: str | None
    status: str
    created_at: datetime
    admin_note: str | None = None


# ------------------------------------------------------------ noticias/recursos


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    category: str
    category_label: str
    excerpt: str | None
    content: str
    image_url: str | None
    city: str | None
    contact_url: str | None
    is_published: bool
    published_at: datetime


class NewsItemOut(BaseModel):
    """Nota de un medio externo: titular, resumen corto y enlace a la fuente."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: str | None
    url: str
    image_url: str | None
    source: str
    tone: str
    is_pet_related: bool
    cities: str | None
    published_at: datetime


class NewsListOut(BaseModel):
    items: list[NewsItemOut]
    total: int
    page: int
    page_size: int
    pages: int


class ArticleIn(BaseModel):
    title: Annotated[str, Field(min_length=3, max_length=200)]
    category: str = "noticia"
    excerpt: Annotated[str, Field(max_length=400)] | None = None
    content: Annotated[str, Field(min_length=10)]
    image_url: Annotated[str, Field(max_length=600)] | None = None
    city: Annotated[str, Field(max_length=80)] | None = None
    contact_url: Annotated[str, Field(max_length=400)] | None = None
    is_published: bool = True

    @field_validator("category")
    @classmethod
    def valid_category(cls, value: str) -> str:
        if value not in ARTICLE_CATEGORIES:
            raise ValueError(f"Categoría no válida. Opciones: {', '.join(ARTICLE_CATEGORIES)}")
        return value


# ------------------------------------------------------------------ administración


class VisitIn(BaseModel):
    """Aviso de visita que manda el frontend en cada cambio de pantalla."""

    # La ruta se acepta por compatibilidad pero no se guarda: el contador es
    # solo un total diario, sin rastro de por dónde navegó cada persona.
    path: Annotated[str, Field(max_length=200)] | None = None
    new_session: bool = False


class AdminStatsOut(BaseModel):
    total_posts: int
    active_posts: int
    lost: int
    found: int
    adoption: int
    resolved: int
    pending_reports: int
    users: int
    posts_last_7_days: int
    top_cities: list[dict]
    # Visitas: `visits` son las del sitio completo; `total_post_views` suma las
    # aperturas de publicaciones, que se contaban desde antes.
    visits: dict
    total_post_views: int
    most_viewed: list[dict]


class AdminPostFlagIn(BaseModel):
    is_active: bool
    hidden_reason: Annotated[str, Field(max_length=200)] | None = None


class AdminReportUpdateIn(BaseModel):
    status: Literal["pendiente", "revisado", "descartado"]
    admin_note: Annotated[str, Field(max_length=1000)] | None = None
    hide_post: bool = False


class AdminUserUpdateIn(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None


# --------------------------------------------------------------------- geografía


class CityOut(BaseModel):
    country: str
    region: str
    city: str
    label: str
