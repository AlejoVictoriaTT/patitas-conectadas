<script setup>
/**
 * Actualidad: notas de medios externos traídas por RSS.
 *
 * Es contenido ajeno, y la interfaz lo deja claro en todo momento: el nombre
 * del medio siempre visible, el enlace abre fuera del sitio y en ningún caso se
 * reproduce el cuerpo de la nota. Las guías propias viven en otra sección para
 * que nadie confunda quién escribió qué.
 *
 * Se muestran de a pocas y con paginación porque son muchas y ocupan pantalla;
 * además el servidor borra las que pasan de diez días, así que aquí solo hay
 * información que todavía sirve.
 */
import { computed, onMounted, ref, watch } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import { api } from '@/api/client'
import { timeAgo } from '@/lib/format'
import { setPageDescription, setPageTitle } from '@/lib/head'

const news = ref([])
const tones = ref([])
const regions = ref([])
const tone = ref('')
const region = ref('')
const onlyPets = ref(false)
const loading = ref(true)

const page = ref(1)
const pages = ref(1)
const total = ref(0)
const PAGE_SIZE = 12

// Ancla para el scroll al cambiar de página.
const gridRef = ref(null)

const TONE_ICONS = {
  esperanza: '🌱',
  ayuda: '🤝',
  tragedia: '🔴',
}

const hayFiltros = computed(() => Boolean(tone.value || region.value || onlyPets.value))

function toneLabel(valor) {
  return tones.value.find((t) => t.value === valor)?.label || valor
}

async function loadNews(nuevaPagina = page.value) {
  loading.value = true
  try {
    const data = await api.news({
      tone: tone.value,
      region: region.value,
      only_pets: onlyPets.value,
      page: nuevaPagina,
      page_size: PAGE_SIZE,
    })
    news.value = data.items
    page.value = data.page
    pages.value = data.pages
    total.value = data.total
  } catch {
    news.value = []
    total.value = 0
    pages.value = 1
  } finally {
    loading.value = false
  }
}

async function irAPagina(destino) {
  if (destino < 1 || destino > pages.value) return
  await loadNews(destino)
  // Se sube hasta la primera noticia, no hasta el inicio de la página: quien
  // pasa de página quiere seguir leyendo, no volver a ver el título y los
  // filtros que ya usó. El margen deja el encabezado fijo sin tapar la tarjeta.
  const destinoY = gridRef.value?.getBoundingClientRect().top ?? 0
  window.scrollTo({
    top: window.scrollY + destinoY - 90,
    behavior: 'smooth',
  })
}

function limpiarFiltros() {
  tone.value = ''
  region.value = ''
  onlyPets.value = false
}

onMounted(async () => {
  setPageTitle('Noticias')
  setPageDescription(
    'Lo que publican los medios sobre la emergencia en Colombia, con una mezcla equilibrada ' +
      'entre lo que pasó y lo que se está haciendo para ayudar.',
  )
  try {
    ;[tones.value, regions.value] = await Promise.all([api.newsTones(), api.newsRegions()])
  } catch {
    tones.value = []
    regions.value = []
  }
  await loadNews(1)
})

// Cualquier cambio de filtro vuelve a la primera página: conservar la página 7
// al cambiar de tono dejaría la pantalla en blanco.
watch([tone, region, onlyPets], () => loadNews(1))
</script>

<template>
  <div class="container section">
    <h1>Noticias</h1>
    <p class="text-soft intro">
      Titulares de medios de comunicación sobre la emergencia. Procuramos una mezcla: lo que está
      pasando, pero también lo que se está haciendo para salir adelante.
    </p>

    <!-- Filtros -->
    <div class="panel filters">
      <div class="field">
        <span class="label">Departamento</span>
        <div class="chip-group">
          <button type="button" class="chip" :class="{ 'is-selected': !region }" @click="region = ''">
            Todos
          </button>
          <button
            v-for="item in regions"
            :key="item.value"
            type="button"
            class="chip"
            :class="{ 'is-selected': region === item.value }"
            :title="`Incluye ${item.capital} y su área`"
            @click="region = item.value"
          >
            {{ item.label }}
          </button>
        </div>
      </div>

      <div class="field">
        <span class="label">Qué quieres leer</span>
        <div class="chip-group">
          <button type="button" class="chip" :class="{ 'is-selected': !tone }" @click="tone = ''">
            Equilibrado
          </button>
          <button
            v-for="item in tones"
            :key="item.value"
            type="button"
            class="chip"
            :class="{ 'is-selected': tone === item.value }"
            @click="tone = item.value"
          >
            {{ TONE_ICONS[item.value] || '·' }} {{ item.label }}
          </button>

          <!--
            Este no es un tono más: es un interruptor que se combina con el tono
            elegido. Va separado por una línea para que se note que pertenece a
            otro eje, y `aria-pressed` expone su estado a los lectores de
            pantalla (los de tono usan `is-selected` a secas).
          -->
          <span class="chip-divider" aria-hidden="true"></span>
          <button
            type="button"
            class="chip"
            :class="{ 'is-selected': onlyPets }"
            :aria-pressed="onlyPets"
            @click="onlyPets = !onlyPets"
          >
            🐾 Solo mascotas
          </button>
        </div>
      </div>

      <button v-if="hayFiltros" class="btn btn-quiet btn-sm clear" type="button" @click="limpiarFiltros">
        Quitar filtros
      </button>
    </div>

    <p v-if="loading" class="text-soft">Cargando noticias…</p>

    <template v-else-if="news.length">
      <p class="text-soft count">
        {{ total }} {{ total === 1 ? 'noticia' : 'noticias' }} ·
        página {{ page }} de {{ pages }}
      </p>

      <div ref="gridRef" class="news-grid stagger">
        <a
          v-for="(item, index) in news"
          :key="item.id"
          class="card news-card"
          :class="`tone-${item.tone}`"
          :style="{ '--i': index }"
          :href="item.url"
          target="_blank"
          rel="noopener noreferrer"
        >
          <div v-if="item.image_url" class="news-photo">
            <img :src="item.image_url" :alt="item.title" loading="lazy" decoding="async" />
          </div>

          <div class="card-body">
            <div class="news-meta">
              <span class="badge" :class="`badge-tone-${item.tone}`">
                {{ TONE_ICONS[item.tone] }} {{ toneLabel(item.tone) }}
              </span>
              <span v-if="item.is_pet_related" class="badge badge-neutral">🐾 Mascotas</span>
            </div>

            <h2>{{ item.title }}</h2>
            <p v-if="item.summary" class="text-soft small summary">{{ item.summary }}</p>

            <p class="text-muted small source-line">
              <strong>{{ item.source }}</strong>
              · {{ timeAgo(item.published_at) }}
              <span class="external" aria-hidden="true">↗</span>
            </p>
          </div>
        </a>
      </div>

      <div v-if="pages > 1" class="pager">
        <button class="btn btn-ghost btn-sm" type="button" :disabled="page <= 1" @click="irAPagina(page - 1)">
          ← Anteriores
        </button>
        <span class="text-soft small">{{ page }} / {{ pages }}</span>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="page >= pages" @click="irAPagina(page + 1)">
          Siguientes →
        </button>
      </div>
    </template>

    <EmptyState
      v-else
      emoji="🗞️"
      title="No hay noticias para estos filtros"
      message="Puede que aún no se haya publicado nada reciente sobre este departamento. Prueba quitando algún filtro."
    >
      <button v-if="hayFiltros" class="btn btn-primary" type="button" @click="limpiarFiltros">
        Ver todas las noticias
      </button>
    </EmptyState>

    <div class="alert alert-info guides-link">
      <div>
        <strong>¿Buscas qué hacer o a quién llamar?</strong>
        <p class="small">
          Los teléfonos de emergencia están en la sección Emergencia, y las guías para buscar o
          cuidar a una mascota, en Guías.
        </p>
        <div class="row-tight">
          <router-link class="btn btn-ghost btn-sm" to="/emergencia">Emergencia</router-link>
          <router-link class="btn btn-quiet btn-sm" to="/guias">Guías</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.intro { max-width: 64ch; margin-top: -6px; }

.filters { margin-bottom: 14px; }
.filters .field:last-of-type { margin-bottom: 0; }

.disclaimer { max-width: 68ch; margin: 0 0 18px; }
.count { margin: 0 0 12px; }

/* Con 12 tarjetas el paso por defecto haría esperar casi un segundo a la
   última: se acorta para que la rejilla entre de corrido. */
.news-grid { display: grid; gap: 14px; grid-auto-rows: 1fr; --stagger-step: 35ms; }

.news-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  color: var(--text);
  /* Franja de color por tono: se distingue de un vistazo sin leer la etiqueta. */
  border-left: 4px solid var(--cerrada);
  transition:
    transform var(--dur) var(--ease-out),
    box-shadow var(--dur) var(--ease-out);
}
.news-card:hover {
  text-decoration: none;
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.news-card.tone-esperanza { border-left-color: var(--encontrada); }
.news-card.tone-ayuda { border-left-color: var(--brand); }
.news-card.tone-tragedia { border-left-color: var(--perdida); }

.news-photo { aspect-ratio: 16 / 9; overflow: hidden; background: var(--surface-2); }
.news-photo img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.5s var(--ease-out); }
.news-card:hover .news-photo img { transform: scale(1.05); }

.news-card .card-body { display: flex; flex-direction: column; gap: 8px; flex: 1; }
.news-meta { display: flex; flex-wrap: wrap; gap: 6px; }
.news-card h2 { margin: 0; font-size: 1.02rem; line-height: 1.35; }

.summary {
  margin: 0;
  /* Tres líneas como máximo: mantiene la rejilla pareja. */
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.source-line { margin: auto 0 0; padding-top: 4px; }
.external { opacity: 0.6; }

.badge-tone-esperanza { background: var(--encontrada-soft); color: #027a48; }
.badge-tone-ayuda { background: var(--brand-light); color: var(--brand-dark); }
.badge-tone-tragedia { background: var(--perdida-soft); color: #b42318; }

.clear { margin-top: 4px; }

/* Separa los chips de tono (selección única) del interruptor de mascotas. */
.chip-divider {
  align-self: center;
  width: 1px;
  height: 24px;
  margin-inline: 4px;
  background: var(--border-strong);
}

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 20px;
}

.guides-link { margin-top: 28px; }
.guides-link p { margin: 4px 0 10px; }

@media (min-width: 768px) {
  .news-grid { grid-template-columns: repeat(2, 1fr); }
  .filters { display: grid; grid-template-columns: minmax(240px, 320px) 1fr; gap: 0 24px; align-items: start; }
}

@media (min-width: 1024px) {
  .news-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>
