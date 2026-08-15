"""Ingesta de noticias de medios por RSS.

Qué hace: lee los feeds públicos de varios medios, se queda con las notas que
hablan del terremoto del 10 de agosto de 2026 y sus ciudades, las clasifica por
tono y las guarda.

Qué NO hace, a propósito:

* No copia el texto de la nota. Guarda titular, el resumen que el propio feed
  publica y el enlace al medio. Republicar el cuerpo completo sería apropiarse
  de trabajo ajeno; enviar tráfico a la fuente no.
* No inventa ni reescribe titulares. Lo que se muestra es lo que el medio dijo.

El tono existe por una razón editorial: una lista donde solo hay muertos y
derrumbes abruma y ahuyenta. Se clasifica cada nota en «esperanza», «ayuda» o
«emergencia» para poder mostrar una mezcla equilibrada.
"""

from __future__ import annotations

import math
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .models import NewsItem, utcnow

# --------------------------------------------------------------------- feeds

# Solo feeds verificados que responden XML. Si un medio cambia su URL, la
# ingesta lo salta y sigue con los demás: nunca falla entera por uno solo.
FEEDS: list[tuple[str, str]] = [
    ("El Tiempo", "https://www.eltiempo.com/rss/colombia.xml"),
    ("El Tiempo", "https://www.eltiempo.com/rss/colombia_otras-ciudades.xml"),
    ("Infobae", "https://www.infobae.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("Semana", "https://www.semana.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("El País (Cali)", "https://www.elpais.com.co/arc/outboundfeeds/rss/?outputType=xml"),
    ("El Universal", "https://www.eluniversal.com.co/arc/outboundfeeds/rss/?outputType=xml"),
]

# Ventana de vigencia. Una noticia de emergencia deja de ser útil rápido: a los
# diez días ya no informa, solo ocupa pantalla. Se usa para dos cosas — no
# ingerir notas más viejas que esto, y borrar las que lo superen.
DIAS_DE_VIGENCIA = 10

# ------------------------------------------------------------- clasificación

# Una nota entra si menciona el evento. Sin esto entraría toda la actualidad
# del país, que no es lo que se busca.
PALABRAS_EVENTO = (
    "terremoto", "sismo", "temblor", "replica", "epicentro", "damnificad",
    "magnitud 7", "escombros", "zona de desastre", "calamidad publica",
)

# Departamentos golpeados el 10 de agosto de 2026, cada uno con su capital y los
# municipios que aparecen en la cobertura. Se agrupan así para poder filtrar por
# departamento: una nota sobre Dosquebradas es una nota de Risaralda aunque no
# nombre el departamento ni una sola vez.
DEPARTAMENTOS = {
    "Valle del Cauca": (
        "Valle del Cauca", "Cali", "Buenaventura", "Tuluá", "Cartago",
        "Palmira", "Buga", "Sevilla", "Yumbo", "Jamundí",
    ),
    "Risaralda": ("Risaralda", "Pereira", "Dosquebradas", "Santa Rosa de Cabal", "La Virginia"),
    "Caldas": ("Caldas", "Manizales", "Villamaría", "Chinchiná", "La Dorada"),
    "Quindío": ("Quindío", "Armenia", "Calarcá", "Montenegro", "Quimbaya"),
    "Chocó": ("Chocó", "Quibdó", "San José del Palmar", "Istmina", "Condoto", "Tadó"),
}

# Lista plana para la detección en el texto.
CIUDADES = tuple(dict.fromkeys(m for municipios in DEPARTAMENTOS.values() for m in municipios))

# Terremotos de otros países. Los feeds regionales (Infobae) cubren toda
# Latinoamérica, así que sin este filtro se cuelan sismos de Indonesia o Perú.
PAISES_EXTRANJEROS = (
    "indonesia", "peru", "mexico", "chile", "japon", "turquia", "ecuador",
    "afganistan", "filipinas", "california", "grecia", "italia", "taiwan",
    "nepal", "birmania", "myanmar", "marruecos", "siria", "iran", "china",
    "guatemala", "nicaragua", "costa rica", "venezuela", "argentina", "bolivia",
)

# El orden importa: se evalúa «ayuda», luego «esperanza», y lo que sobra queda
# como «emergencia». Así una nota de «cómo donar» no se clasifica como tragedia
# solo porque también nombre a las víctimas.
PALABRAS_AYUDA = (
    "como ayudar", "donacion", "donacione", "donar", "dono", "donan", "donara",
    "centro de acopio", "centros de acopio", "colecta", "ayuda humanitaria",
    "ayudas humanitarias", "voluntari", "brigada", "albergue", "refugio",
    "punto de recoleccion", "puntos de recoleccion", "vaki", "recaudo",
    "linea de atencion", "buscador de personas", "como reportar", "se unen para",
)

PALABRAS_ESPERANZA = (
    "rescat", "sobrevivi", "con vida", "reencuentr", "salvo", "salvad",
    "milagro", "solidarid", "reconstru", "reabr", "restablec", "esperanza",
    "heroe", "heroina", "hallaron con vida", "sano y salvo", "sana y salva",
    "vuelve a abrir", "regresan a casa",
)

PALABRAS_MASCOTAS = (
    "mascota", "animal", "perro", "perra", "gato", "gata", "canino", "felino",
    "veterinari", "zoonosis", "cuatro patas", "peludo", "cachorro",
)

# Si el TITULAR habla de muertes o duelo, la nota es de emergencia aunque el
# resumen mencione una donación. Etiquetar de «esperanza» la historia de una
# persona que murió sería, además de impreciso, ofensivo.
PALABRAS_DUELO = (
    "murio", "muerte", "muertos", "muertas", "fallecid", "luto", "funeral",
    "entierro", "cadaver", "victimas fatales", "desaparecid", "entre lagrimas",
    "tragedia", "duelo", "sepult", "no sobrevivio", "perdio la vida",
    # «sin vida» va aquí a propósito: es la fórmula con la que los medios
    # anuncian que la búsqueda terminó mal.
    "sin vida",
)

# …salvo que el propio titular cuente un final feliz.
PALABRAS_FINAL_FELIZ = ("rescatad", "con vida", "sobrevivi", "sano y salvo", "sana y salva")


def _sin_tildes(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto or "")
    return normalizado.encode("ascii", "ignore").decode("ascii").lower()


def _compilar(palabras: tuple[str, ...]) -> re.Pattern:
    """Compila las palabras para que coincidan solo al INICIO de una palabra.

    Es la diferencia entre acertar y no: sin el límite de palabra, «Cali»
    coincide dentro de «calidad» y «Buga» dentro de cualquier apellido, y el
    feed se llena de notas que no tienen nada que ver.

    Se ancla el inicio pero no el final, para que «rescat» siga cubriendo
    «rescate», «rescatado» y «rescatistas».
    """
    alternativas = "|".join(re.escape(p) for p in palabras)
    return re.compile(rf"\b(?:{alternativas})", re.IGNORECASE)


RE_EVENTO = _compilar(PALABRAS_EVENTO)
RE_AYUDA = _compilar(PALABRAS_AYUDA)
RE_ESPERANZA = _compilar(PALABRAS_ESPERANZA)
RE_MASCOTAS = _compilar(PALABRAS_MASCOTAS)
RE_EXTRANJERO = _compilar(PAISES_EXTRANJEROS)
RE_DUELO = _compilar(PALABRAS_DUELO)
RE_FINAL_FELIZ = _compilar(PALABRAS_FINAL_FELIZ)
RE_COLOMBIA = _compilar(tuple(_sin_tildes(c) for c in CIUDADES) + ("colombia", "colombian"))

_CIUDAD_RE = {ciudad: _compilar((_sin_tildes(ciudad),)) for ciudad in CIUDADES}


def clasificar_tono(titulo_plano: str, texto_plano: str) -> str:
    # El duelo en el titular manda sobre todo lo demás.
    if RE_DUELO.search(titulo_plano) and not RE_FINAL_FELIZ.search(titulo_plano):
        return "tragedia"
    if RE_AYUDA.search(texto_plano):
        return "ayuda"
    if RE_ESPERANZA.search(texto_plano):
        return "esperanza"
    return "tragedia"


def detectar_ciudades(texto: str) -> list[str]:
    plano = _sin_tildes(texto)
    return [ciudad for ciudad, patron in _CIUDAD_RE.items() if patron.search(plano)]


# Los blogs «minuto a minuto» publican entradas cuyo titular es solo la hora.
RE_TITULAR_FECHA = re.compile(
    r"^\s*(lunes|martes|miercoles|miércoles|jueves|viernes|sabado|sábado|domingo)?[\s,]*"
    r"\d{1,2}\s+de\s+\w+|^\s*\d{1,2}:\d{2}",
    re.IGNORECASE,
)


def es_titular_basura(titulo: str) -> bool:
    """Descarta titulares que no son noticias: horas sueltas, fechas, vacíos."""
    limpio = titulo.strip()
    if len(limpio) < 25:
        return True
    return bool(RE_TITULAR_FECHA.match(limpio))


def es_relevante(titulo_plano: str, texto_plano: str) -> bool:
    """Decide si una nota entra al feed.

    Tres condiciones, todas necesarias:

    1. Habla del evento (sismo, terremoto, damnificados…). Nombrar una ciudad
       no basta: si no, entraría toda la actualidad de Cali.
    2. Ocurre en Colombia. Los feeds regionales cubren el continente entero.
    3. El titular no es sobre un sismo de otro país. Se mira solo el titular
       porque el resumen suele arrastrar enlaces a notas relacionadas.
    """
    if not RE_EVENTO.search(texto_plano):
        return False
    if not RE_COLOMBIA.search(texto_plano):
        return False
    if RE_EXTRANJERO.search(titulo_plano):
        return False
    return True


# ------------------------------------------------------------------ parseo

@dataclass
class Entrada:
    external_id: str
    title: str
    summary: str | None
    url: str
    image_url: str | None
    source: str
    tone: str
    is_pet_related: bool
    cities: str | None
    published_at: datetime


ETIQUETAS_HTML = re.compile(r"<[^>]+>")
ESPACIOS = re.compile(r"\s+")


def _limpiar(texto: str | None, maximo: int) -> str | None:
    if not texto:
        return None
    limpio = ESPACIOS.sub(" ", ETIQUETAS_HTML.sub("", texto)).strip()
    if not limpio:
        return None
    if len(limpio) <= maximo:
        return limpio
    # Se corta en la última palabra completa para no dejar sílabas sueltas.
    recorte = limpio[:maximo].rsplit(" ", 1)[0]
    return f"{recorte}…"


def _fecha(texto: str | None) -> datetime:
    if not texto:
        return utcnow()
    for parseador in (parsedate_to_datetime, datetime.fromisoformat):
        try:
            fecha = parseador(texto.strip())
            return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
    return utcnow()


def _texto(item: ET.Element, *nombres: str) -> str | None:
    for nombre in nombres:
        valor = item.findtext(nombre)
        if valor and valor.strip():
            return valor.strip()
    return None


def _imagen(item: ET.Element) -> str | None:
    enclosure = item.find("enclosure")
    if enclosure is not None:
        url = enclosure.get("url")
        if url and str(enclosure.get("type", "")).startswith("image"):
            return url
    # media:content / media:thumbnail (namespace de Media RSS)
    for etiqueta in ("{http://search.yahoo.com/mrss/}content", "{http://search.yahoo.com/mrss/}thumbnail"):
        nodo = item.find(etiqueta)
        if nodo is not None and nodo.get("url"):
            return nodo.get("url")
    return None


def parsear_feed(xml: str, fuente: str) -> list[Entrada]:
    """Convierte el XML de un feed en entradas ya clasificadas y filtradas."""
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError:
        return []

    canal = raiz.find("channel")
    items = canal.findall("item") if canal is not None else raiz.findall(".//item")

    limite = utcnow() - timedelta(days=DIAS_DE_VIGENCIA)
    entradas: list[Entrada] = []

    for item in items:
        titulo = _texto(item, "title")
        enlace = _texto(item, "link", "guid")
        if not titulo or not enlace or es_titular_basura(titulo):
            continue

        descripcion = _texto(item, "description", "{http://purl.org/rss/1.0/modules/content/}encoded")
        # La clasificación mira titular + resumen: el titular solo se queda corto.
        titulo_plano = _sin_tildes(titulo)
        plano = _sin_tildes(f"{titulo} {descripcion or ''}")

        if not es_relevante(titulo_plano, plano):
            continue

        publicado = _fecha(_texto(item, "pubDate", "{http://purl.org/dc/elements/1.1/}date"))
        if publicado < limite:
            continue

        ciudades = detectar_ciudades(f"{titulo} {descripcion or ''}")

        entradas.append(
            Entrada(
                external_id=(_texto(item, "guid") or enlace)[:400],
                title=_limpiar(titulo, 290) or titulo[:290],
                summary=_limpiar(descripcion, 480),
                url=enlace[:600],
                image_url=(_imagen(item) or "")[:600] or None,
                source=fuente,
                tone=clasificar_tono(titulo_plano, plano),
                is_pet_related=bool(RE_MASCOTAS.search(plano)),
                cities=", ".join(ciudades)[:300] or None,
                published_at=publicado,
            )
        )

    return entradas


# ------------------------------------------------------------------ ingesta

async def descargar(url: str, cliente: httpx.AsyncClient) -> str | None:
    try:
        respuesta = await cliente.get(url)
        if respuesta.status_code >= 400:
            return None
        return respuesta.text
    except httpx.HTTPError:
        return None


def purgar_antiguas(db: Session) -> int:
    """Borra las noticias que salieron de la ventana de vigencia.

    Se ejecuta en cada sincronización para que la tabla no crezca sin control y
    la sección no acumule notas que ya nadie va a leer.
    """
    limite = utcnow() - timedelta(days=DIAS_DE_VIGENCIA)
    borradas = db.query(NewsItem).filter(NewsItem.published_at < limite).delete(
        synchronize_session=False
    )
    db.commit()
    return int(borradas or 0)


async def sincronizar(db: Session) -> dict:
    """Descarga todos los feeds, guarda lo nuevo y borra lo vencido."""
    cabeceras = {
        # Algunos medios rechazan peticiones sin user-agent.
        "user-agent": "PatitasConectadasBot/1.0 (+https://patitas-conectadas.vercel.app)",
        "accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
    }

    entradas: list[Entrada] = []
    fuentes_ok = 0
    fuentes_fallidas: list[str] = []

    async with httpx.AsyncClient(timeout=20, headers=cabeceras, follow_redirects=True) as cliente:
        for nombre, url in FEEDS:
            xml = await descargar(url, cliente)
            if xml is None:
                fuentes_fallidas.append(nombre)
                continue
            fuentes_ok += 1
            entradas.extend(parsear_feed(xml, nombre))

    # Un mismo hecho aparece en varios feeds: se deduplica por identificador.
    unicas: dict[str, Entrada] = {}
    for entrada in entradas:
        unicas.setdefault(entrada.external_id, entrada)

    purgadas = purgar_antiguas(db)

    if not unicas:
        return {
            "nuevas": 0,
            "revisadas": 0,
            "purgadas": purgadas,
            "fuentes_ok": fuentes_ok,
            "fuentes_fallidas": fuentes_fallidas,
        }

    existentes = set(
        db.scalars(
            select(NewsItem.external_id).where(NewsItem.external_id.in_(list(unicas)))
        ).all()
    )

    nuevas = 0
    for external_id, entrada in unicas.items():
        if external_id in existentes:
            continue
        db.add(
            NewsItem(
                external_id=entrada.external_id,
                title=entrada.title,
                summary=entrada.summary,
                url=entrada.url,
                image_url=entrada.image_url,
                source=entrada.source,
                tone=entrada.tone,
                is_pet_related=entrada.is_pet_related,
                cities=entrada.cities,
                published_at=entrada.published_at,
            )
        )
        nuevas += 1

    db.commit()
    return {
        "nuevas": nuevas,
        "revisadas": len(unicas),
        "purgadas": purgadas,
        "fuentes_ok": fuentes_ok,
        "fuentes_fallidas": fuentes_fallidas,
    }


# ----------------------------------------------------------------- lectura

def _mezclar_por_tono(items: list[NewsItem], limite: int) -> list[NewsItem]:
    """Arma una lista equilibrada en vez de un muro de tragedias.

    Regla: como mucho un 40% de notas de emergencia. El resto se llena con
    esperanza y ayuda, y lo relacionado con mascotas va primero por ser el tema
    de la plataforma. Si no hay suficientes notas positivas, se completa con las
    que haya: es preferible mostrar menos variedad que dejar la sección vacía.
    """
    cupo_tragedia = max(1, round(limite * 0.4))

    def orden(item: NewsItem):
        return (not item.is_pet_related, -item.published_at.timestamp())

    positivas = sorted([i for i in items if i.tone != "tragedia"], key=orden)
    tragicas = sorted([i for i in items if i.tone == "tragedia"], key=orden)

    seleccion = positivas[: limite - min(cupo_tragedia, len(tragicas))]
    seleccion += tragicas[:cupo_tragedia]

    # Si faltó material positivo, se rellena con el resto disponible.
    if len(seleccion) < limite:
        restantes = [i for i in positivas + tragicas if i not in seleccion]
        seleccion += restantes[: limite - len(seleccion)]

    return sorted(seleccion, key=lambda i: -i.published_at.timestamp())


def _filtrar(tone: str | None, region: str | None, only_pets: bool):
    consulta = select(NewsItem).where(NewsItem.is_published.is_(True))
    if tone:
        consulta = consulta.where(NewsItem.tone == tone)
    if region:
        # Una nota cuenta como del departamento si menciona el departamento o
        # cualquiera de sus municipios.
        municipios = DEPARTAMENTOS.get(region)
        if municipios:
            consulta = consulta.where(
                or_(*[NewsItem.cities.ilike(f"%{m}%") for m in municipios])
            )
        else:
            consulta = consulta.where(NewsItem.cities.ilike(f"%{region}%"))
    if only_pets:
        consulta = consulta.where(NewsItem.is_pet_related.is_(True))
    return consulta


def listar(
    db: Session,
    *,
    tone: str | None = None,
    region: str | None = None,
    only_pets: bool = False,
    page: int = 1,
    page_size: int = 6,
) -> dict:
    """Devuelve una página de noticias más el total, para poder paginar.

    La primera página se equilibra por tono para que nadie se encuentre de
    entrada un muro de tragedias. A partir de la segunda se ordena por fecha sin
    más: quien pide «ver más» ya decidió seguir leyendo, y a esas alturas
    reordenar solo confundiría sobre qué es lo reciente.
    """
    consulta = _filtrar(tone, region, only_pets)

    total = int(
        db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    )

    if page <= 1 and not tone:
        # Se traen de más para que la mezcla tenga de dónde escoger.
        candidatas = list(
            db.scalars(
                consulta.order_by(NewsItem.published_at.desc()).limit(max(page_size * 4, 32))
            ).all()
        )
        items = _mezclar_por_tono(candidatas, page_size)
    else:
        items = list(
            db.scalars(
                consulta.order_by(NewsItem.published_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)) if total else 1,
    }
