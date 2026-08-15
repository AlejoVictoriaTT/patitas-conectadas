<script setup>
/**
 * Guías y consejos: contenido propio de la plataforma.
 *
 * Los teléfonos de emergencia y los enlaces oficiales viven en `/emergencia`.
 * Estaban aquí y la página quedaba saturada: son dos necesidades distintas —
 * esto se lee con calma, aquello se busca con urgencia.
 */
import { onMounted, ref, watch } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import CitySelect from '@/components/CitySelect.vue'
import { api } from '@/api/client'
import { categoryIcon, categoryLabel, formatShortDate } from '@/lib/format'
import { setPageDescription, setPageTitle } from '@/lib/head'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()

const articles = ref([])
const categories = ref([])
const category = ref('')
const city = ref(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    articles.value = await api.articles({ category: category.value, city: city.value?.city, limit: 40 })
  } catch {
    articles.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  setPageTitle('Guías y consejos')
  setPageDescription(
    'Qué hacer si tu mascota se perdió, cómo ayudar a una que encontraste, esterilización, ' +
      'vacunación, hogares de paso y adopción responsable.',
  )
  if (ui.city) city.value = ui.city
  try {
    categories.value = await api.articleCategories()
  } catch {
    categories.value = []
  }
  await load()
})

watch([category, city], load)
</script>

<template>
  <div class="container section">
    <header class="page-head">
      <div>
        <h1>Guías y consejos</h1>
        <p class="text-soft lead">
          Qué hacer si tu mascota se perdió, cómo ayudar a una que encontraste y lo que conviene
          saber antes de esterilizar, vacunar o adoptar.
        </p>
      </div>

      <aside class="emergency-card">
        <strong>¿Es una emergencia?</strong>
        <p>Los teléfonos y los enlaces oficiales están en su propia sección, para encontrarlos rápido.</p>
        <router-link class="btn btn-ghost btn-sm" to="/emergencia">Ver teléfonos de emergencia</router-link>
      </aside>
    </header>

    <div class="filters panel">
      <div class="field">
        <span class="label">Ciudad</span>
        <CitySelect v-model="city" allow-clear placeholder="Todo el país" />
        <p class="hint">Los recursos sin ciudad aplican a todo el país.</p>
      </div>

      <div class="field">
        <span class="label">Categoría</span>
        <div class="chip-group">
          <button type="button" class="chip" :class="{ 'is-selected': !category }" @click="category = ''">
            Todo
          </button>
          <button
            v-for="item in categories"
            :key="item.value"
            type="button"
            class="chip"
            :class="{ 'is-selected': category === item.value }"
            @click="category = item.value"
          >
            {{ categoryIcon(item.value) }} {{ item.label }}
          </button>
        </div>
      </div>
    </div>

    <p v-if="loading" class="text-soft">Cargando…</p>

    <div v-else-if="articles.length" class="article-grid stagger">
      <article
        v-for="(item, index) in articles"
        :key="item.id"
        class="card article-card"
        :style="{ '--i': index % 8 }"
      >
        <img v-if="item.image_url" :src="item.image_url" :alt="item.title" loading="lazy" />
        <div class="card-body">
          <span class="badge badge-neutral">{{ categoryIcon(item.category) }} {{ categoryLabel(item) }}</span>
          <h2>
            <router-link :to="`/guias/${item.slug}`">{{ item.title }}</router-link>
          </h2>
          <p class="text-soft small">{{ item.excerpt || item.content.slice(0, 140) + '…' }}</p>
          <p class="text-muted small">
            {{ formatShortDate(item.published_at) }}
            <template v-if="item.city"> · {{ item.city }}</template>
          </p>
        </div>
      </article>
    </div>

    <EmptyState
      v-else
      emoji="📄"
      title="Todavía no hay contenido en esta categoría"
      message="Pronto publicaremos recursos e información de ayuda para tu ciudad."
    />
  </div>
</template>

<style scoped>
.page-head { display: grid; gap: 16px; margin-bottom: 22px; }
.page-head h1 { margin-bottom: 4px; }
.lead { margin: 0; max-width: 52ch; }

.emergency-card {
  display: grid;
  gap: 6px;
  justify-items: start;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-left: 4px solid var(--perdida);
  border-radius: var(--radius);
  background: var(--surface);
}
.emergency-card p { margin: 0 0 4px; font-size: 0.9rem; color: var(--text-soft); }

.filters { margin-bottom: 20px; }
.filters .field:last-child { margin-bottom: 0; }

.article-grid { display: grid; gap: 14px; grid-auto-rows: 1fr; }

.article-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  transition:
    transform var(--dur) var(--ease-out),
    box-shadow var(--dur) var(--ease-out),
    border-color var(--dur) var(--ease-out);
}
.article-card:hover,
.article-card:focus-within {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--brand-light);
}

.article-card img { width: 100%; aspect-ratio: 16 / 9; object-fit: cover; }
.article-card .card-body { display: flex; flex-direction: column; gap: 8px; flex: 1; }
.article-card h2 { font-size: 1.08rem; margin: 0; line-height: 1.35; }
.article-card h2 a { color: var(--text); }
.article-card p { margin: 0; }
.article-card .badge { align-self: flex-start; }
.article-card .card-body p:last-child { margin-top: auto; padding-top: 4px; }

@media (min-width: 860px) {
  .page-head {
    grid-template-columns: 1fr minmax(260px, 340px);
    align-items: center;
    gap: 28px;
  }
}

@media (min-width: 768px) {
  .article-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (min-width: 1024px) {
  .article-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>
