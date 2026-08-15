"""Almacenamiento de fotografías.

Producción: Vercel Blob (API REST, sin SDK).
Desarrollo: carpeta local `backend/uploads` servida por FastAPI en `/uploads`.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

import httpx

from .config import settings

BLOB_API = "https://blob.vercel-storage.com"
BLOB_API_VERSION = "7"

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}


class StorageError(Exception):
    pass


def build_object_path(content_type: str, prefix: str = "mascotas") -> str:
    extension = ALLOWED_CONTENT_TYPES.get(content_type, ".jpg")
    stamp = datetime.now(timezone.utc).strftime("%Y/%m")
    return f"{prefix}/{stamp}/{secrets.token_hex(12)}{extension}"


async def upload_image(data: bytes, content_type: str, prefix: str = "mascotas") -> str:
    """Sube la imagen y devuelve su URL pública."""
    path = build_object_path(content_type, prefix)

    if settings.blob_token:
        return await _upload_to_vercel_blob(path, data, content_type)
    if settings.is_serverless:
        # El disco de la función es efímero y /uploads no se sirve en producción:
        # guardar aquí crearía publicaciones con fotos rotas.
        raise StorageError(
            "El almacenamiento de fotos no está configurado. "
            "Crea el Blob store en Vercel y define BLOB_READ_WRITE_TOKEN."
        )
    return _save_locally(path, data)


async def _upload_to_vercel_blob(path: str, data: bytes, content_type: str) -> str:
    headers = {
        "authorization": f"Bearer {settings.blob_token}",
        "x-api-version": BLOB_API_VERSION,
        "x-content-type": content_type,
        "x-add-random-suffix": "1",
        "x-cache-control-max-age": "31536000",
        "content-type": content_type,
    }
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.put(f"{BLOB_API}/{path}", content=data, headers=headers)
    except httpx.HTTPError as exc:  # pragma: no cover - depende de la red
        raise StorageError(f"No se pudo conectar con el almacenamiento: {exc}") from exc

    if response.status_code >= 400:
        raise StorageError(f"El almacenamiento rechazó la imagen ({response.status_code}): {response.text[:200]}")

    payload = response.json()
    url = payload.get("url") or payload.get("downloadUrl")
    if not url:
        raise StorageError("El almacenamiento no devolvió una URL válida.")
    return url


def _save_locally(path: str, data: bytes) -> str:
    target = settings.upload_dir / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"/uploads/{path}"


async def delete_image(url: str) -> None:
    """Borra la imagen del almacenamiento. Los fallos no interrumpen el flujo."""
    if not url:
        return
    if url.startswith("/uploads/"):
        target = settings.upload_dir / url[len("/uploads/"):]
        target.unlink(missing_ok=True)
        return
    if not settings.blob_token or not url.startswith("https://"):
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"{BLOB_API}/delete",
                json={"urls": [url]},
                headers={
                    "authorization": f"Bearer {settings.blob_token}",
                    "x-api-version": BLOB_API_VERSION,
                },
            )
    except httpx.HTTPError:
        pass
