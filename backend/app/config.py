"""Configuración leída desde variables de entorno.

En local se puede usar un archivo `.env` en la raíz del proyecto (ver `.env.example`).
En Vercel las variables se definen en el panel del proyecto.
"""

import os
from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    """Carga un `.env` simple sin dependencias externas (solo desarrollo)."""
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def _normalize_database_url(url: str) -> str:
    """Adapta la URL de Neon/Vercel Postgres al driver `psycopg` (v3)."""
    if not url:
        return ""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class Settings:
    def __init__(self) -> None:
        self.app_name: str = _env("APP_NAME", default="Patitas Conectadas")
        self.environment: str = _env("VERCEL_ENV", "ENVIRONMENT", default="development")
        self.is_serverless: bool = bool(os.environ.get("VERCEL"))

        # URL pública del sitio (para enlaces compartidos, OAuth y metadatos OG)
        site_url = _env("SITE_URL", "PUBLIC_SITE_URL")
        if not site_url:
            vercel_url = _env("VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_URL")
            site_url = f"https://{vercel_url}" if vercel_url else "http://localhost:5173"
        self.site_url: str = site_url.rstrip("/")

        # Base de datos: Neon/Vercel Postgres en producción, SQLite en local
        raw_db = _env("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL")
        self.database_url: str = _normalize_database_url(raw_db) or (
            f"sqlite:///{(ROOT_DIR / 'backend' / 'patitas.db').as_posix()}"
        )
        self.is_sqlite: bool = self.database_url.startswith("sqlite")

        # Autenticación
        self.jwt_secret: str = _env("JWT_SECRET", default="desarrollo-inseguro-cambiar-en-produccion")
        self.jwt_algorithm: str = "HS256"
        self.jwt_expire_minutes: int = int(_env("JWT_EXPIRE_MINUTES", default="43200"))  # 30 días
        self.google_client_id: str = _env("GOOGLE_CLIENT_ID")
        self.google_client_secret: str = _env("GOOGLE_CLIENT_SECRET")

        # Almacenamiento de fotos (Vercel Blob)
        self.blob_token: str = _env("BLOB_READ_WRITE_TOKEN")
        # En serverless el disco es de solo lectura salvo /tmp (efímero entre invocaciones).
        self.upload_dir: Path = (
            Path("/tmp/patitas-uploads") if self.is_serverless else ROOT_DIR / "backend" / "uploads"
        )
        self.max_photos: int = int(_env("MAX_PHOTOS", default="5"))
        self.max_upload_bytes: int = int(_env("MAX_UPLOAD_BYTES", default=str(6 * 1024 * 1024)))

        # Antispam opcional (Cloudflare Turnstile). Si está vacío, no se exige captcha.
        self.turnstile_secret: str = _env("TURNSTILE_SECRET")

        # Correos que reciben rol de administrador automáticamente
        self.admin_emails: set[str] = {
            e.strip().lower() for e in _env("ADMIN_EMAILS").split(",") if e.strip()
        }

        # Orígenes permitidos para CORS en desarrollo
        self.cors_origins: list[str] = [
            o.strip()
            for o in _env(
                "CORS_ORIGINS",
                default="http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if o.strip()
        ]

    @property
    def google_redirect_uri(self) -> str:
        return f"{self.site_url}/api/auth/google/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
