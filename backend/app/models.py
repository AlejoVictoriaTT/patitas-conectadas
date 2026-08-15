"""Modelos de datos.

Entidades: Usuario, Publicación (mascota), Fotografía, Reporte, Noticia/Recurso
y el contador diario de visitas.
Se mantiene una separación clara entre ellas para poder crecer sin romper la V1.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# --------------------------------------------------------------------------------------
# Vocabulario del dominio (se usan strings para no depender de tipos ENUM de la BD)
# --------------------------------------------------------------------------------------

TYPE_LOST = "perdida"
TYPE_FOUND = "encontrada"
TYPE_ADOPTION = "adopcion"
POST_TYPES = (TYPE_LOST, TYPE_FOUND, TYPE_ADOPTION)

# Estados por tipo de publicación
STATUS_LOST_ACTIVE = "perdida"            # 🔴 Perdida
STATUS_LOST_REUNITED = "reunida"          # 🟢 Encontrada / reunida con su familia
STATUS_FOUND_ACTIVE = "buscando_familia"  # 🟢 Encontrada — buscando a su familia
STATUS_FOUND_DELIVERED = "entregada"      # 🏠 Entregada a su familia
STATUS_ADOPTION_ACTIVE = "disponible"     # 💙 Disponible para adopción
STATUS_ADOPTION_DONE = "adoptada"         # 🏠 Adoptada
STATUS_CLOSED = "cerrada"                 # ⚫ Caso cerrado

INITIAL_STATUS = {
    TYPE_LOST: STATUS_LOST_ACTIVE,
    TYPE_FOUND: STATUS_FOUND_ACTIVE,
    TYPE_ADOPTION: STATUS_ADOPTION_ACTIVE,
}

ALLOWED_STATUSES = {
    TYPE_LOST: (STATUS_LOST_ACTIVE, STATUS_LOST_REUNITED, STATUS_CLOSED),
    TYPE_FOUND: (STATUS_FOUND_ACTIVE, STATUS_FOUND_DELIVERED, STATUS_CLOSED),
    TYPE_ADOPTION: (STATUS_ADOPTION_ACTIVE, STATUS_ADOPTION_DONE, STATUS_CLOSED),
}

# Estados que significan "el caso terminó bien / ya no está activo"
RESOLVED_STATUSES = (
    STATUS_LOST_REUNITED,
    STATUS_FOUND_DELIVERED,
    STATUS_ADOPTION_DONE,
    STATUS_CLOSED,
)

SPECIES = ("perro", "gato", "otro")
SEXES = ("macho", "hembra", "desconocido")
SIZES = ("pequeno", "mediano", "grande")

REPORT_REASONS = (
    "informacion_falsa",
    "contenido_inapropiado",
    "duplicada",
    "venta_de_animales",
    "spam",
    "maltrato",
    "otro",
)


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(20), default="email", nullable=False)
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    posts: Mapped[list["Post"]] = relationship(back_populates="owner")


class Post(Base):
    """Publicación de mascota perdida, encontrada o en adopción."""

    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Identificador corto y público usado en la URL (ej. "a1b2c3d4")
    public_id: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)

    type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)

    # Datos de la mascota
    species: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    pet_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    breed: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    age: Mapped[str | None] = mapped_column(String(60), nullable=True)
    color: Mapped[str | None] = mapped_column(String(80), nullable=True)
    size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    has_collar: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_tag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    special_marks: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Ubicación (la dirección exacta nunca se expone públicamente)
    country: Mapped[str] = mapped_column(String(60), default="Colombia", nullable=False)
    region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    city: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    neighborhood: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Fechas
    event_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Contacto (al menos uno de whatsapp / phone / email)
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_whatsapp: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Propietario: usuario registrado o invitado con token de administración
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    guest_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manage_token_hash: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)

    # Moderación y métricas
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    hidden_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reports_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    owner: Mapped["User | None"] = relationship(back_populates="posts")
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="Photo.position",
    )
    reports: Mapped[list["Report"]] = relationship(back_populates="post", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_posts_city_type_status", "city", "type", "status"),
        Index("ix_posts_active_created", "is_active", "created_at"),
    )

    @property
    def primary_photo(self) -> "Photo | None":
        for photo in self.photos:
            if photo.is_primary:
                return photo
        return self.photos[0] if self.photos else None

    @property
    def is_resolved(self) -> bool:
        return self.status in RESOLVED_STATUSES


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    post_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(600), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    post: Mapped["Post"] = relationship(back_populates="photos")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    post_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    reporter_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reporter_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pendiente", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    post: Mapped["Post"] = relationship(back_populates="reports")


class Article(Base):
    """Noticias y recursos: albergues, jornadas, consejos, bienestar animal."""

    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="noticia", index=True, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(600), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    contact_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    @property
    def category_label(self) -> str:
        return ARTICLE_CATEGORY_LABELS.get(self.category, (self.category or "").replace("_", " "))


class NewsItem(Base):
    """Noticia de un medio externo, traída automáticamente por RSS.

    Se guarda deliberadamente en su propia tabla y no en `Article`: los
    artículos son contenido propio y curado, y esto es material de terceros
    del que solo conservamos titular, resumen corto y enlace a la fuente.
    Mezclarlos obligaría además a migrar la tabla existente en producción.

    Nunca se almacena el texto completo de la nota: eso le pertenece al medio.
    """

    __tablename__ = "news_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Identificador de la nota en su feed (guid o enlace): evita duplicados.
    external_id: Mapped[str] = mapped_column(String(400), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(600), nullable=True)
    url: Mapped[str] = mapped_column(String(600), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(600), nullable=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    # tragedia | esperanza | ayuda — permite equilibrar lo que se muestra.
    tone: Mapped[str] = mapped_column(String(20), default="tragedia", index=True, nullable=False)
    # Habla de mascotas o animales: se prioriza por ser el tema de la plataforma.
    is_pet_related: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Ciudades detectadas en el titular, separadas por coma.
    cities: Mapped[str | None] = mapped_column(String(300), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


NEWS_TONES = ("esperanza", "ayuda", "tragedia")

NEWS_TONE_LABELS = {
    "esperanza": "Esperanza",
    "ayuda": "Cómo ayudar",
    "tragedia": "Emergencia",
}


class SiteVisit(Base):
    """Contador diario de visitas al sitio.

    No guarda nada de la persona: solo cuántas páginas se vieron ese día y
    cuántas sesiones distintas las abrieron. Es un agregado por fecha, así que
    la tabla crece una fila por día, no una por visita.

    `views` cuenta cada cambio de pantalla; `sessions` cuenta la primera visita
    de cada pestaña del navegador, que es la aproximación a «personas».
    """

    __tablename__ = "site_visits"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


ARTICLE_CATEGORIES = (
    "noticia",
    "albergue",
    "hogar_de_paso",
    "fundacion",
    "jornada_adopcion",
    "esterilizacion",
    "vacunacion",
    "consejo",
    "bienestar_animal",
)

# Los valores guardados no llevan tilde porque son identificadores; el texto que
# se muestra sí, y sale siempre de aquí.
ARTICLE_CATEGORY_LABELS = {
    "noticia": "Noticia",
    "albergue": "Albergue",
    "hogar_de_paso": "Hogar de paso",
    "fundacion": "Fundación",
    "jornada_adopcion": "Jornada de adopción",
    "esterilizacion": "Esterilización",
    "vacunacion": "Vacunación",
    "consejo": "Consejo",
    "bienestar_animal": "Bienestar animal",
}
