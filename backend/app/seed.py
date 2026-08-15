"""Datos iniciales.

Uso:
    python -m backend.app.seed                      # crea tablas + contenido de ayuda
    python -m backend.app.seed --demo               # añade publicaciones de ejemplo
    python -m backend.app.seed --admin correo@x.com --password Secreta123
"""

from __future__ import annotations

import argparse
from datetime import timedelta
from urllib.parse import quote

from sqlalchemy import func, select

from .db import SessionLocal, init_db
from .models import (
    INITIAL_STATUS,
    TYPE_ADOPTION,
    TYPE_FOUND,
    TYPE_LOST,
    Article,
    Photo,
    Post,
    User,
    utcnow,
)
from .security import hash_password
from .utils import generate_public_id, slugify

PALETA = {
    TYPE_LOST: ("#F04438", "#FEE4E2"),
    TYPE_FOUND: ("#12B76A", "#D1FADF"),
    TYPE_ADOPTION: ("#2E90FA", "#D1E9FF"),
}


def placeholder_photo(texto: str, tipo: str) -> str:
    """SVG en línea para los datos de demostración (no requiere red ni almacenamiento)."""
    color, fondo = PALETA.get(tipo, ("#7A5AF8", "#ECE9FE"))
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 600'>"
        f"<rect width='600' height='600' fill='{fondo}'/>"
        f"<circle cx='300' cy='250' r='120' fill='{color}' opacity='.25'/>"
        f"<text x='300' y='285' font-size='120' text-anchor='middle'>&#128054;</text>"
        f"<text x='300' y='430' font-size='42' font-family='sans-serif' text-anchor='middle' fill='{color}'>"
        f"{texto}</text></svg>"
    )
    return "data:image/svg+xml;utf8," + quote(svg)


# Guías de la plataforma.
#
# Sobre el tono: quien lee esto casi siempre está asustado, con culpa o con
# prisa. Los textos hablan de frente, en segunda persona, y reconocen lo que la
# persona está sintiendo antes de darle instrucciones. Sin emojis, sin signos de
# admiración y sin frases de autoayuda: la calidez está en lo que se dice, no en
# la decoración.
ARTICULOS = [
    {
        "title": "Las primeras 24 horas: qué hacer si tu mascota se perdió",
        "category": "consejo",
        "excerpt": (
            "El primer día es el que más pesa. Esto es lo que conviene hacer, en orden, "
            "mientras el rastro todavía está fresco."
        ),
        "content": (
            "Lo primero: respira. La mayoría de los animales perdidos aparecen, y muchos lo hacen "
            "cerca de casa. Vas a necesitar la cabeza fría para las próximas horas, así que "
            "concéntrate en lo que sí puedes hacer ahora mismo.\n\n"
            "Empieza por tu propia cuadra. Un animal asustado no corre lejos: se esconde. Revisa "
            "debajo de los carros, detrás de las materas, en los antejardines y en cualquier hueco "
            "donde quepa. Llámalo con la voz de todos los días, la que usas para darle comida. Si "
            "gritas, el miedo lo hará quedarse quieto justo donde está.\n\n"
            "Publica de una vez, aunque sientas que es pronto. Una foto clara, la ciudad y el "
            "barrio bastan para empezar. Cada hora que pasa el círculo de búsqueda se hace más "
            "grande, y mientras más ojos estén mirando, mejor.\n\n"
            "Después mueve el enlace por donde de verdad circula la gente de tu zona: el grupo de "
            "WhatsApp del conjunto, el del edificio, el de la cuadra. Ahí es donde alguien va a "
            "reconocerlo.\n\n"
            "Pregúntale a quienes se pasan el día en la calle. El portero, la señora de la tienda, "
            "el de la panadería, los domiciliarios, quienes reciclan. Ven todo lo que pasa en el "
            "sector y suelen acordarse de un animal que anda solo.\n\n"
            "Deja algo tuyo en la puerta. Su cobija, su cama, unas medias que hayas usado. El olor "
            "familiar orienta a muchos animales de vuelta a casa, sobre todo de noche.\n\n"
            "Y revisa todos los días las publicaciones de mascota encontrada de tu ciudad, además "
            "de los albergues y las veterinarias cercanas. Es frecuente que alguien ya la haya "
            "recogido y esté buscándote a ti."
        ),
    },
    {
        "title": "Encontraste una mascota: cómo ayudarla a volver a casa",
        "category": "consejo",
        "excerpt": (
            "Unos minutos bien invertidos al principio pueden ahorrar semanas de búsqueda "
            "a la familia que la está esperando."
        ),
        "content": (
            "Gracias por detenerte. Mucha gente pasa de largo, y ese animal tiene ahora una "
            "posibilidad real de volver a casa.\n\n"
            "Antes de nada, revísale el cuello. Un collar, una placa, una manilla, cualquier cosa "
            "con un número puede resolverlo todo en una llamada. Tómale también una foto de frente, "
            "con buena luz y sin filtros.\n\n"
            "Si puedes, pasa por una veterinaria y pide que le lean el microchip. La lectura es "
            "rápida y en muchos sitios no cobran por hacerla. Es la forma más directa de dar con "
            "su familia.\n\n"
            "Cuando publiques, hazlo como mascota encontrada e indica el sector donde la viste. "
            "Aquí va el consejo más importante de todos: guárdate un detalle que solo su familia "
            "podría conocer. Una cicatriz, una mancha en un lugar poco visible, el nombre al que "
            "responde. Ese dato es la manera de confirmar que quien reclama es quien dice ser.\n\n"
            "No la entregues sin verificar. Pide fotos anteriores, el carné de vacunación o "
            "cualquier documento de la veterinaria. Una familia de verdad tiene todo eso y lo "
            "muestra sin problema."
        ),
    },
    {
        "title": "Cómo tomar la foto que hará que alguien la reconozca",
        "category": "consejo",
        "excerpt": (
            "La foto es lo primero y a veces lo único que la gente mira. Vale la pena "
            "dedicarle dos minutos."
        ),
        "content": (
            "Piensa en quién va a ver esa foto: alguien que baja rápido por una lista en el "
            "celular, entre otras cosas que está haciendo. Tiene un segundo para reconocer al "
            "animal. Ese segundo es todo lo que tienes.\n\n"
            "Busca luz natural, cerca de una ventana o afuera, y agáchate hasta quedar a su "
            "altura. Una foto tomada desde arriba deforma las proporciones y hace que un perro "
            "mediano parezca pequeño.\n\n"
            "Que en la primera foto se vea el cuerpo entero. Es lo que permite calcular el tamaño "
            "real. Añade una segunda de la cara, de frente, y una tercera de lo que lo hace "
            "distinto a cualquier otro: la mancha del lomo, la oreja caída, la cicatriz, el collar "
            "que llevaba puesto.\n\n"
            "No uses filtros. Un pelaje café que sale dorado en la pantalla hace que la gente "
            "descarte al animal correcto sin darse cuenta."
        ),
    },
    {
        "title": "Esterilización: la decisión que evita el abandono antes de que ocurra",
        "category": "esterilizacion",
        "excerpt": (
            "Casi todos los municipios del país hacen jornadas gratuitas. Así funcionan "
            "y qué esperar después de la cirugía."
        ),
        "content": (
            "Detrás de cada animal en la calle hubo una camada que nadie planeó. Esterilizar es "
            "la forma más eficaz de cortar esa cadena, y también le hace bien a tu mascota: "
            "reduce el riesgo de varios tumores e infecciones, y disminuye las ganas de escaparse "
            "a buscar pareja, que es una de las causas más comunes de que se pierdan.\n\n"
            "La mayoría de las alcaldías organizan jornadas gratuitas durante todo el año. Se "
            "anuncian por barrios y casi siempre piden inscripción previa, así que conviene estar "
            "pendiente de la Secretaría de Salud o de Ambiente de tu municipio y de sus redes.\n\n"
            "El día de la cirugía llévala en ayunas, según lo que te indiquen, y con transporte de "
            "regreso resuelto. Es un procedimiento de rutina, pero va a salir adormilada.\n\n"
            "Los días siguientes son los que importan. Reposo de verdad, nada de saltar ni correr, "
            "el collar isabelino puesto aunque proteste, y revisar la herida a diario. Si notas "
            "hinchazón, mal olor o secreción, vuelve a la veterinaria sin esperar."
        ),
    },
    {
        "title": "Vacuna antirrábica: cuándo ponerla y por qué no se aplaza",
        "category": "vacunacion",
        "excerpt": (
            "Es gratuita en las jornadas oficiales de casi todos los municipios y protege "
            "a tu mascota, a tu familia y a tu barrio."
        ),
        "content": (
            "La rabia sigue existiendo en Colombia y no tiene cura una vez aparecen los síntomas. "
            "Por eso la vacuna es obligatoria, y por eso el Estado la pone gratis: no se trata solo "
            "de tu mascota, sino de todos los que viven a su alrededor.\n\n"
            "Perros y gatos reciben la primera dosis a partir de los tres meses y un refuerzo cada "
            "año. Las jornadas oficiales se anuncian por barrios; también puedes preguntar en el "
            "centro de salud más cercano por el calendario del año.\n\n"
            "Lleva siempre el carné de vacunación. Es el documento que demuestra que tu mascota "
            "está al día, y te lo van a pedir para viajar, para mudarte a un conjunto o si alguna "
            "vez hay un incidente con una mordedura.\n\n"
            "Si tu mascota está enferma, convaleciente o preñada, no la vacunes ese día. Consulta "
            "primero con un veterinario y reprograma."
        ),
    },
    {
        "title": "Ser hogar de paso: lo que implica de verdad",
        "category": "hogar_de_paso",
        "excerpt": (
            "Es el eslabón que más falta hace y el que menos gente conoce. "
            "Esto es lo que se necesita para serlo."
        ),
        "content": (
            "Un hogar de paso recibe a un animal rescatado por un tiempo: mientras se recupera de "
            "una cirugía, mientras baja el miedo, mientras aparece la familia definitiva. No es "
            "adoptar, y ahí está justamente su valor. Una sola casa puede acompañar a muchos "
            "animales a lo largo de un año.\n\n"
            "En la mayoría de los casos la fundación cubre los gastos veterinarios y el alimento. "
            "Lo que aportas tú es lo que no se puede comprar: un lugar tranquilo, rutina, paseos y "
            "el trato paciente que necesita un animal que la pasó mal.\n\n"
            "Antes de decir que sí, habla con todas las personas de la casa y piensa en los "
            "animales que ya viven contigo. Un hogar de paso funciona cuando todos están de "
            "acuerdo, no cuando uno solo se entusiasma.\n\n"
            "Y sí, se encariña uno. Casi todo el mundo llora el día de la entrega. También casi "
            "todo el mundo vuelve a recibir al siguiente, porque ver a ese animal entrar a su "
            "nueva casa compensa el resto."
        ),
    },
    {
        "title": "Antes de adoptar: cinco preguntas que conviene responder con calma",
        "category": "bienestar_animal",
        "excerpt": (
            "Adoptar es un compromiso de diez a veinte años. Pensarlo bien no es "
            "desconfianza, es responsabilidad."
        ),
        "content": (
            "Adoptar es de las decisiones más bonitas que se pueden tomar, y también una de las "
            "que más se toman por impulso. Estas preguntas no existen para desanimarte, sino para "
            "que el animal que llegue no tenga que volver a irse.\n\n"
            "¿Cuántas horas al día va a quedarse solo? Un perro joven que pasa diez horas encerrado "
            "no está mal cuidado por maldad, pero tampoco está bien.\n\n"
            "¿El presupuesto del mes aguanta el alimento, las vacunas y, sobre todo, una urgencia? "
            "Una cirugía imprevista puede costar varios salarios mínimos, y suele llegar sin avisar.\n\n"
            "¿El tamaño y la energía encajan con tu casa y tu rutina? Un animal muy activo en un "
            "apartamento pequeño con alguien que trabaja todo el día es una fuente de problemas "
            "para ambos.\n\n"
            "¿Están de acuerdo todas las personas con las que vives? Incluidas las que hoy dicen "
            "que sí sin mucho entusiasmo.\n\n"
            "¿Qué pasa si te mudas, viajas o cambia tu situación? Vale la pena tener una respuesta "
            "antes, no después.\n\n"
            "Si alguna te dejó dudando, no lo descartes todo: ser hogar de paso o apadrinar a un "
            "animal en una fundación son formas reales de ayudar que piden menos de lo que tú "
            "quizá no puedas dar hoy."
        ),
    },
    {
        "title": "Albergues y fundaciones: cómo acercarse y cómo aparecer aquí",
        "category": "fundacion",
        "excerpt": (
            "Directorio en construcción de organizaciones que atienden animales en "
            "situación de calle."
        ),
        "content": (
            "Este directorio va creciendo ciudad por ciudad. Si diriges una fundación, un albergue "
            "o una red de hogares de paso y quieres aparecer, escríbenos desde la sección de "
            "contacto y lo revisamos.\n\n"
            "Si encontraste un animal y estás pensando en llevarlo a un albergue, llama antes. "
            "Casi todos trabajan al límite de su capacidad y con presupuestos que no alcanzan; "
            "llegar sin avisar los pone en una situación difícil y a veces significa que no puedan "
            "recibirlo.\n\n"
            "Vale la pena saber que hay otras formas de ayudar además de llevar animales: los "
            "albergues siempre necesitan alimento, medicamentos, transporte a citas veterinarias y "
            "personas que dediquen unas horas al aseo o a los paseos. Preguntar qué les hace falta "
            "esta semana suele ser más útil que suponerlo."
        ),
    },
]

DEMO_POSTS = [
    {
        "type": TYPE_LOST,
        "species": "perro",
        "pet_name": "Max",
        "breed": "Criollo",
        "sex": "macho",
        "color": "Café con blanco",
        "size": "mediano",
        "has_collar": True,
        "description": "Se perdió cerca del parque Caldas. Lleva collar azul y responde al nombre de Max. Es muy asustadizo con las motos.",
        "city": "Manizales",
        "region": "Caldas",
        "neighborhood": "Palermo",
        "days_ago": 2,
        "whatsapp": "3101234567",
    },
    {
        "type": TYPE_FOUND,
        "species": "gato",
        "pet_name": None,
        "breed": "Mestizo",
        "sex": "hembra",
        "color": "Gris atigrado",
        "size": "pequeno",
        "description": "Fue encontrada cerca de la iglesia del barrio. Es tranquila y parece estar acostumbrada a las personas. Está en un hogar temporal mientras aparece su familia.",
        "city": "Manizales",
        "region": "Caldas",
        "neighborhood": "La Enea",
        "days_ago": 1,
        "whatsapp": "3157654321",
    },
    {
        "type": TYPE_ADOPTION,
        "species": "perro",
        "pet_name": "Luna",
        "breed": "Labrador mestiza",
        "sex": "hembra",
        "color": "Negra",
        "size": "grande",
        "description": "Es cariñosa, juguetona y busca una familia responsable. Está esterilizada, desparasitada y con vacunas al día.",
        "city": "Medellín",
        "region": "Antioquia",
        "neighborhood": "Laureles",
        "days_ago": 5,
        "whatsapp": "3009876543",
    },
    {
        "type": TYPE_LOST,
        "species": "gato",
        "pet_name": "Simón",
        "breed": "Siamés",
        "sex": "macho",
        "color": "Beige con café",
        "size": "pequeno",
        "has_tag": True,
        "description": "Salió por la ventana el fin de semana. Tiene placa con número de teléfono y una mancha oscura en la pata trasera derecha.",
        "city": "Bogotá",
        "region": "Bogotá D.C.",
        "neighborhood": "Chapinero",
        "days_ago": 4,
        "whatsapp": "3204455667",
    },
    {
        "type": TYPE_ADOPTION,
        "species": "gato",
        "pet_name": "Nina",
        "breed": "Criolla",
        "sex": "hembra",
        "color": "Blanco y negro",
        "size": "pequeno",
        "description": "Rescatada de la calle hace tres meses. Ya está socializada, usa arenera y convive bien con otros gatos.",
        "city": "Cali",
        "region": "Valle del Cauca",
        "neighborhood": "San Fernando",
        "days_ago": 9,
        "whatsapp": "3183322110",
    },
    {
        "type": TYPE_FOUND,
        "species": "perro",
        "pet_name": None,
        "breed": "Pastor mestizo",
        "sex": "macho",
        "color": "Negro con fuego",
        "size": "grande",
        "description": "Apareció en la portería del conjunto, muy flaco y con hambre. Está bien cuidado mientras aparece su familia.",
        "city": "Pereira",
        "region": "Risaralda",
        "neighborhood": "Cuba",
        "days_ago": 3,
        "whatsapp": "3115566778",
    },
]


def seed_articles(db, *, refresh: bool = False) -> tuple[int, int]:
    """Crea las guías que falten. Con `refresh`, además reescribe las existentes.

    Sin `refresh` no se toca nada de lo que ya está en la base: si alguien editó
    un texto desde el panel, un seed rutinario no debe pisárselo. `--refresh` es
    la forma explícita de decir «quiero los textos nuevos».

    El emparejamiento es por slug, que se deriva del título. Si el título cambió,
    el artículo viejo se queda y se crea uno nuevo; por eso también se busca por
    categoría cuando el slug no aparece.
    """
    creados = 0
    actualizados = 0

    for data in ARTICULOS:
        slug = slugify(data["title"], max_length=120)
        existente = db.scalar(select(Article).where(Article.slug == slug))

        if existente is None and refresh:
            # El título pudo haber cambiado: se intenta emparejar por categoría.
            existente = db.scalar(
                select(Article).where(Article.category == data["category"]).order_by(Article.created_at)
            )

        if existente is None:
            db.add(Article(slug=slug, **data))
            creados += 1
            continue

        if not refresh:
            continue

        existente.slug = slug
        for campo, valor in data.items():
            setattr(existente, campo, valor)
        actualizados += 1

    db.commit()
    return creados, actualizados


def seed_demo_posts(db) -> int:
    creados = 0
    for data in DEMO_POSTS:
        nombre = data.get("pet_name") or f"{data['species']}-{data['city']}"
        if db.scalar(
            select(func.count())
            .select_from(Post)
            .where(Post.pet_name == data.get("pet_name"), Post.city == data["city"], Post.type == data["type"])
        ):
            continue

        public_id = generate_public_id()
        etiqueta = data.get("pet_name") or ("Encontrado" if data["type"] == TYPE_FOUND else "En adopción")
        post = Post(
            public_id=public_id,
            slug=f"{slugify(nombre)}-{public_id}",
            type=data["type"],
            status=INITIAL_STATUS[data["type"]],
            species=data["species"],
            pet_name=data.get("pet_name"),
            breed=data.get("breed"),
            sex=data.get("sex"),
            color=data.get("color"),
            size=data.get("size"),
            has_collar=data.get("has_collar"),
            has_tag=data.get("has_tag"),
            description=data["description"],
            country="Colombia",
            region=data["region"],
            city=data["city"],
            neighborhood=data.get("neighborhood"),
            event_date=(utcnow() - timedelta(days=data["days_ago"])).date(),
            created_at=utcnow() - timedelta(days=data["days_ago"]),
            contact_name="Equipo Patitas",
            contact_whatsapp=f"57{data['whatsapp']}",
        )
        post.photos.append(Photo(url=placeholder_photo(etiqueta, data["type"]), position=0, is_primary=True))
        db.add(post)
        creados += 1
    db.commit()
    return creados


def create_admin(db, email: str, password: str, name: str = "Administrador") -> str:
    user = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user:
        user.is_admin = True
        if password:
            user.password_hash = hash_password(password)
        db.commit()
        return f"Usuario existente actualizado como administrador: {email}"

    db.add(
        User(
            name=name,
            email=email.lower(),
            password_hash=hash_password(password),
            auth_provider="email",
            is_admin=True,
        )
    )
    db.commit()
    return f"Administrador creado: {email}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Datos iniciales de Patitas Conectadas")
    parser.add_argument("--demo", action="store_true", help="Crear publicaciones de ejemplo")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Reescribir el texto de las guías que ya existen (pisa ediciones hechas desde el panel)",
    )
    parser.add_argument("--admin", help="Correo del administrador a crear/promover")
    parser.add_argument("--password", help="Contraseña del administrador")
    args = parser.parse_args()

    init_db()
    print("Tablas verificadas.")

    with SessionLocal() as db:
        creados, actualizados = seed_articles(db, refresh=args.refresh)
        print(f"Guías creadas: {creados} · actualizadas: {actualizados}")
        if args.demo:
            print(f"Publicaciones de ejemplo creadas: {seed_demo_posts(db)}")
        if args.admin:
            if not args.password:
                parser.error("--admin requiere --password")
            print(create_admin(db, args.admin, args.password))


if __name__ == "__main__":
    main()
