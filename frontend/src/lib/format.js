/** Formato de fechas, etiquetas y textos según el tipo de publicación. */

const MESES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]

function toDate(value) {
  if (!value) return null
  // Las fechas sin hora (YYYY-MM-DD) se interpretan en horario local, no UTC.
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T12:00:00`) : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(value) {
  const date = toDate(value)
  if (!date) return ''
  return `${date.getDate()} de ${MESES[date.getMonth()]} de ${date.getFullYear()}`
}

export function formatShortDate(value) {
  const date = toDate(value)
  if (!date) return ''
  return `${date.getDate()} ${MESES[date.getMonth()].slice(0, 3)} ${date.getFullYear()}`
}

export function timeAgo(value) {
  const date = toDate(value)
  if (!date) return ''
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return 'hace un momento'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `hace ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `hace ${hours} h`
  const days = Math.floor(hours / 24)
  if (days === 1) return 'ayer'
  if (days < 30) return `hace ${days} días`
  const months = Math.floor(days / 30)
  if (months < 12) return `hace ${months} ${months === 1 ? 'mes' : 'meses'}`
  const years = Math.floor(months / 12)
  return `hace ${years} ${years === 1 ? 'año' : 'años'}`
}

export function todayISO() {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

export const TYPE_META = {
  perdida: {
    emoji: '🔴',
    label: 'Perdida',
    action: 'Perdí una mascota',
    color: 'perdida',
    dateLabel: '¿Qué día se perdió?',
    descriptionHint: 'Se perdió cerca del parque. Lleva collar azul y responde al nombre de Max.',
    resolvedMessage: '🎉 ¡Esta mascota ya fue reunida con su familia!',
  },
  encontrada: {
    emoji: '🟢',
    label: 'Encontrada',
    action: 'Encontré una mascota',
    color: 'encontrada',
    dateLabel: '¿Qué día la encontraste?',
    descriptionHint: 'Fue encontrada cerca de la iglesia. Es tranquila y parece estar acostumbrada a las personas.',
    resolvedMessage: '🏠 Esta mascota ya fue entregada a su familia.',
  },
  adopcion: {
    emoji: '💙',
    label: 'En adopción',
    action: 'Dar en adopción',
    color: 'adopcion',
    dateLabel: '¿Desde qué fecha está disponible?',
    descriptionHint: 'Es cariñosa, juguetona y busca una familia responsable.',
    resolvedMessage: '❤️ Esta mascota ya fue adoptada.',
  },
}

export const SPECIES_EMOJI = {
  perro: '🐕',
  gato: '🐈',
  otro: '🐾',
}

const STATUS_COLOR = {
  perdida: 'perdida',
  reunida: 'encontrada',
  buscando_familia: 'encontrada',
  entregada: 'encontrada',
  disponible: 'adopcion',
  adoptada: 'adopcion',
  cerrada: 'cerrada',
}

export function statusColor(status) {
  return STATUS_COLOR[status] || 'cerrada'
}

export function typeMeta(type) {
  return TYPE_META[type] || TYPE_META.perdida
}

export function speciesEmoji(species) {
  return SPECIES_EMOJI[species] || '🐾'
}

export function locationLine(post) {
  return [post.city, post.neighborhood].filter(Boolean).join(' · ')
}

/* ------------------------------------------------- concordancia de género
   Un perro está «perdido» y una gata está «perdida». La API ya devuelve el
   título y las etiquetas concordadas; lo de aquí abajo es el respaldo para
   respuestas antiguas que aún estén en caché. */

const PET_NOUNS = {
  perro: { macho: 'Perro', hembra: 'Perra' },
  gato: { macho: 'Gato', hembra: 'Gata' },
}

const TYPE_ADJECTIVE = {
  perdida: { m: 'perdido', f: 'perdida' },
  encontrada: { m: 'encontrado', f: 'encontrada' },
  adopcion: { m: 'en adopción', f: 'en adopción' },
}

/** 'm' o 'f': el género del sustantivo que nombra a la mascota. */
export function petGender(post) {
  if (post?.gender) return post.gender
  // Sin sexo registrado se usa el masculino, que es la forma no marcada.
  if (PET_NOUNS[post?.species]) return post.sex === 'hembra' ? 'f' : 'm'
  return 'f' // «Mascota» es femenino
}

export function petNoun(post) {
  const porEspecie = PET_NOUNS[post?.species]
  if (!porEspecie) return 'Mascota'
  return post.sex === 'hembra' ? porEspecie.hembra : porEspecie.macho
}

/** Título visible: el nombre propio, o «Perra perdida» / «Gato encontrado». */
export function postTitle(post) {
  if (!post) return ''
  if (post.title) return post.title
  if (post.pet_name) return post.pet_name
  const adjetivo = (TYPE_ADJECTIVE[post.type] || TYPE_ADJECTIVE.perdida)[petGender(post)]
  return `${petNoun(post)} ${adjetivo}`
}

/** Encabezado de la fecha en el detalle, concordado con la mascota. */
export function eventDateLabel(post) {
  if (post?.type === 'adopcion') return 'Disponible desde:'
  if (post?.type === 'perdida') return 'Se perdió el:'
  return petGender(post) === 'f' ? 'Fue encontrada el:' : 'Fue encontrado el:'
}

/* ------------------------------------------- categorías de Noticias y ayuda */

export const CATEGORY_ICONS = {
  noticia: '📰',
  albergue: '🏚️',
  hogar_de_paso: '🏡',
  fundacion: '🤝',
  jornada_adopcion: '💙',
  esterilizacion: '🏥',
  vacunacion: '💉',
  consejo: '💡',
  bienestar_animal: '🐾',
}

// Los valores se guardan sin tilde porque son identificadores. El texto visible
// viene de la API (`category_label`); esto es el respaldo con la ortografía correcta.
const CATEGORY_LABELS = {
  noticia: 'Noticia',
  albergue: 'Albergue',
  hogar_de_paso: 'Hogar de paso',
  fundacion: 'Fundación',
  jornada_adopcion: 'Jornada de adopción',
  esterilizacion: 'Esterilización',
  vacunacion: 'Vacunación',
  consejo: 'Consejo',
  bienestar_animal: 'Bienestar animal',
}

export function categoryLabel(article) {
  if (typeof article === 'string') return CATEGORY_LABELS[article] || article.replace(/_/g, ' ')
  return article?.category_label || CATEGORY_LABELS[article?.category] || ''
}

export function categoryIcon(category) {
  return CATEGORY_ICONS[category] || '📄'
}
