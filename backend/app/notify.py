"""Alertas cuando entra una publicación nueva.

Todos los proveedores son opcionales. Si no hay ninguno configurado la función
no hace nada y publicar sigue funcionando igual: una alerta jamás puede impedir
que alguien reporte una mascota perdida.

Proveedores, en el orden en que se eligen
-----------------------------------------

`telegram` — el recomendado. Gratuito, oficial, sin límites prácticos para este
uso y sin plantillas que aprobar. Se crea un bot con @BotFather en dos minutos y
funciona en celular y escritorio. Es el que conviene usar.

`callmebot` (WhatsApp) — gratuito pero es un servicio de terceros sin garantías:
cambia el número de activación cada cierto tiempo y no promete entrega.

`whatsapp_cloud` — la API oficial de Meta. Es la opción seria para WhatsApp,
pero fuera de la ventana de 24 horas de conversación solo permite enviar
**plantillas aprobadas**. Como el administrador nunca escribe primero, hay que
crear y aprobar una plantilla con un parámetro de texto e indicarla en
WHATSAPP_TEMPLATE.

Variables de entorno
--------------------

    # Telegram (recomendado)
    TELEGRAM_BOT_TOKEN     token que entrega @BotFather
    TELEGRAM_CHAT_ID       id del chat o grupo que recibe las alertas

    # WhatsApp por CallMeBot
    ALERT_WHATSAPP_TO      número destino en formato internacional (57300...)
    CALLMEBOT_APIKEY       clave que entrega CallMeBot

    # WhatsApp oficial (Meta)
    ALERT_WHATSAPP_TO
    WHATSAPP_TOKEN
    WHATSAPP_PHONE_ID
    WHATSAPP_TEMPLATE      nombre de la plantilla aprobada
    WHATSAPP_TEMPLATE_LANG idioma de la plantilla (por defecto: es)

Para averiguar el TELEGRAM_CHAT_ID:

    python -m backend.app.notify --telegram-chats
"""

from __future__ import annotations

import logging
import os

import httpx

from .config import settings
from .models import RESOLVED_STATUSES, STATUS_CLOSED
from .serializers import post_url
from .utils import pet_gender, post_title, status_label, type_label

logger = logging.getLogger("patitas")

TIMEOUT = 10
TELEGRAM_API = "https://api.telegram.org"


def _env(nombre: str) -> str:
    return os.environ.get(nombre, "").strip()


def destino_whatsapp() -> str:
    """Número que recibe las alertas de WhatsApp, solo dígitos."""
    return "".join(c for c in _env("ALERT_WHATSAPP_TO") if c.isdigit())


def proveedor_activo() -> str | None:
    """Devuelve el proveedor que se va a usar, o None si no hay ninguno."""
    if _env("TELEGRAM_BOT_TOKEN") and _env("TELEGRAM_CHAT_ID"):
        return "telegram"
    if destino_whatsapp() and _env("CALLMEBOT_APIKEY"):
        return "callmebot"
    if destino_whatsapp() and _env("WHATSAPP_TOKEN") and _env("WHATSAPP_PHONE_ID"):
        return "whatsapp_cloud"
    return None


def esta_activo() -> bool:
    return proveedor_activo() is not None


def _lugar(post) -> str:
    return ", ".join(p for p in (post.neighborhood, post.city, post.region) if p)


def construir_mensaje(post) -> str:
    """Alerta de publicación nueva.

    Se llama con la sesión de base de datos todavía abierta. Para personalizar
    el aviso este es el sitio que hay que tocar: el objeto `post` trae todos los
    campos de la publicación (description, breed, color, size, neighborhood,
    contact_name, event_date, special_marks…).
    """
    genero = pet_gender(post.species, post.sex)
    contacto = post.contact_whatsapp or post.contact_phone or post.contact_email or "sin contacto"

    return (
        f"🐾 Nueva publicación en {settings.app_name}\n"
        f"{type_label(post.type, genero).upper()}: {post_title(post)}\n"
        f"📍 {_lugar(post)}\n"
        f"📞 {contacto}\n"
        f"{post_url(post)}"
    )


def construir_mensaje_estado(post, estado_anterior: str) -> str:
    """Alerta de cambio de estado.

    Un caso que se resuelve es una buena noticia y se marca distinto: es lo que
    conviene ver de un vistazo entre muchas notificaciones.
    """
    genero = pet_gender(post.species, post.sex)

    # «Cerrada» también cuenta como resuelta a efectos de la búsqueda, pero no
    # es un final feliz: puede ser que la persona se rindiera. Marcarla con el
    # mismo ✅ que un reencuentro sería celebrar algo que quizá salió mal.
    if post.status == STATUS_CLOSED:
        encabezado = f"⚫ Caso cerrado en {settings.app_name}"
    elif post.status in RESOLVED_STATUSES:
        encabezado = f"✅ Buenas noticias en {settings.app_name}"
    else:
        encabezado = f"🔄 Cambio de estado en {settings.app_name}"

    return (
        f"{encabezado}\n"
        f"{post_title(post)} · {_lugar(post)}\n"
        f"{status_label(estado_anterior, genero)} → {status_label(post.status, genero)}\n"
        f"{post_url(post)}"
    )


# ------------------------------------------------------------------ Telegram


async def _enviar_telegram(cliente: httpx.AsyncClient, texto: str) -> bool:
    respuesta = await cliente.post(
        f"{TELEGRAM_API}/bot{_env('TELEGRAM_BOT_TOKEN')}/sendMessage",
        json={
            "chat_id": _env("TELEGRAM_CHAT_ID"),
            "text": texto,
            # Sin parse_mode: el texto va tal cual y no hay que escapar nada.
            # Con Markdown, un guion bajo en un nombre rompería el mensaje entero.
            "disable_web_page_preview": False,
        },
    )
    if respuesta.status_code >= 400:
        logger.warning("Telegram rechazó la alerta (%s): %s", respuesta.status_code, respuesta.text[:300])
        return False
    return True


# ------------------------------------------------------------------ WhatsApp


async def _enviar_callmebot(cliente: httpx.AsyncClient, texto: str) -> bool:
    respuesta = await cliente.get(
        "https://api.callmebot.com/whatsapp.php",
        params={"phone": destino_whatsapp(), "text": texto, "apikey": _env("CALLMEBOT_APIKEY")},
    )
    return respuesta.status_code < 400


async def _enviar_whatsapp_cloud(cliente: httpx.AsyncClient, texto: str) -> bool:
    phone_id = _env("WHATSAPP_PHONE_ID")
    plantilla = _env("WHATSAPP_TEMPLATE") or "alerta_publicacion"
    idioma = _env("WHATSAPP_TEMPLATE_LANG") or "es"

    respuesta = await cliente.post(
        f"https://graph.facebook.com/v21.0/{phone_id}/messages",
        headers={"Authorization": f"Bearer {_env('WHATSAPP_TOKEN')}"},
        json={
            "messaging_product": "whatsapp",
            "to": destino_whatsapp(),
            "type": "template",
            "template": {
                "name": plantilla,
                "language": {"code": idioma},
                # La plantilla debe tener un único parámetro de texto en el cuerpo.
                "components": [{"type": "body", "parameters": [{"type": "text", "text": texto}]}],
            },
        },
    )
    if respuesta.status_code >= 400:
        logger.warning("WhatsApp Cloud rechazó la alerta (%s): %s", respuesta.status_code, respuesta.text[:300])
        return False
    return True


ENVIADORES = {
    "telegram": _enviar_telegram,
    "callmebot": _enviar_callmebot,
    "whatsapp_cloud": _enviar_whatsapp_cloud,
}


async def enviar(texto: str) -> bool:
    """Manda la alerta ya redactada. Cualquier fallo se registra y se ignora.

    Recibe el texto y no la publicación a propósito: esto corre en una tarea de
    segundo plano, cuando la sesión de base de datos ya se cerró y tocar el
    objeto ORM lanzaría `DetachedInstanceError`. El mensaje se arma antes, en el
    endpoint, mientras la sesión sigue viva.
    """
    proveedor = proveedor_activo()
    if not proveedor:
        return False

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as cliente:
            enviado = await ENVIADORES[proveedor](cliente, texto)
    except httpx.HTTPError as exc:
        logger.warning("No se pudo enviar la alerta por %s: %s", proveedor, exc)
        return False

    if not enviado:
        logger.warning("La alerta por %s no se entregó.", proveedor)
    return enviado


# --------------------------------------------------- utilidad de línea de comandos


async def _listar_chats_telegram() -> None:
    """Imprime los chats que le han escrito al bot, para sacar el TELEGRAM_CHAT_ID."""
    token = _env("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Falta TELEGRAM_BOT_TOKEN. Defínelo en el .env o en el entorno.")
        return

    async with httpx.AsyncClient(timeout=TIMEOUT) as cliente:
        respuesta = await cliente.get(f"{TELEGRAM_API}/bot{token}/getUpdates")

    if respuesta.status_code >= 400:
        print(f"Telegram respondió {respuesta.status_code}: {respuesta.text[:200]}")
        return

    resultados = respuesta.json().get("result", [])
    if not resultados:
        print(
            "El bot no ha recibido ningún mensaje.\n"
            "Abre Telegram, busca tu bot por su @usuario y escríbele cualquier cosa\n"
            "(o /start). Después vuelve a ejecutar este comando."
        )
        return

    vistos = {}
    for update in resultados:
        chat = (update.get("message") or update.get("channel_post") or {}).get("chat")
        if chat:
            vistos[chat["id"]] = chat

    print("Chats encontrados:\n")
    for chat_id, chat in vistos.items():
        nombre = chat.get("title") or " ".join(
            p for p in (chat.get("first_name"), chat.get("last_name")) if p
        )
        usuario = f" (@{chat['username']})" if chat.get("username") else ""
        print(f"  TELEGRAM_CHAT_ID={chat_id}    {chat.get('type')}: {nombre}{usuario}")
    print("\nCopia la línea que corresponda a tu .env o a las variables de Vercel.")


def _main() -> None:
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Utilidades de notificaciones")
    parser.add_argument(
        "--telegram-chats",
        action="store_true",
        help="Listar los chats que le escribieron al bot para obtener el TELEGRAM_CHAT_ID",
    )
    parser.add_argument("--test", action="store_true", help="Enviar un mensaje de prueba")
    args = parser.parse_args()

    if args.telegram_chats:
        asyncio.run(_listar_chats_telegram())
        return

    if args.test:
        proveedor = proveedor_activo()
        if not proveedor:
            print("No hay ningún proveedor configurado. Revisa las variables de entorno.")
            return
        print(f"Enviando prueba por {proveedor}…")
        ok = asyncio.run(
            enviar(
                f"🐾 Mensaje de prueba de {settings.app_name}.\n"
                "Si lo estás leyendo, las alertas quedaron funcionando."
            )
        )
        print("Enviado." if ok else "No se pudo enviar. Revisa los registros del servidor.")
        return

    parser.print_help()


if __name__ == "__main__":
    _main()
