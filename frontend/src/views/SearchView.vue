<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CitySelect from '@/components/CitySelect.vue'
import PetCard from '@/components/PetCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import { api } from '@/api/client'
import { useUiStore } from '@/stores/ui'

const props = defineProps({
  fixedType: { type: String, default: '' },
})

const route = useRoute()
const router = useRouter()
const ui = useUiStore()

const TIPOS = [
  { value: '', label: 'Todas', emoji: '🐾' },
  { value: 'perdida', label: 'Perdidas', emoji: '🔴' },
  { value: 'encontrada', label: 'Encontradas', emoji: '🟢' },
  { value: 'adopcion', label: 'En adopción', emoji: '💙' },
]

const ESPECIES = [
  { value: '', label: 'Todas' },
  { value: 'perro', label: '🐕 Perros' },
  { value: 'gato', label: '🐈 Gatos' },
  { value: 'otro', label: '🐾 Otros' },
]

const filters = reactive({
  type: props.fixedType || route.query.tipo || '',
  species: route.query.especie || '',
  q: route.query.q || '',
  sex: '',
  breed: '',
  color: '',
  date_from: '',
  include_resolved: false,
  sort: 'recientes',
})

const city = ref(
  route.query.ciudad
    ? { country: 'Colombia', region: route.query.departamento || null, city: route.query.ciudad }
    : ui.city,
)

const items = ref([])
const total = ref(0)
const page = ref(1)
const pages = ref(1)
const loading = ref(true)

const title = computed(() =>
  props.fixedType === 'adopcion' ? '💙 Mascotas en adopción' : '🔎 Buscar mascotas',
)

const activeFilters = computed(() => {
  const list = []
  if (city.value) list.push(`📍 ${city.value.city}`)
  if (filters.species) list.push(ESPECIES.find((e) => e.value === filters.species)?.label)
  if (filters.q) list.push(`«${filters.q}»`)
  if (filters.include_resolved) list.push('Incluye casos resueltos')
  return list.filter(Boolean)
})

async function load(reset = true) {
  if (reset) page.value = 1
  loading.value = true
  try {
    const data = await api.listPosts({
      type: props.fixedType || filters.type,
      species: filters.species,
      q: filters.q,
      sex: filters.sex,
      breed: filters.breed,
      color: filters.color,
      date_from: filters.date_from,
      include_resolved: filters.include_resolved,
      sort: filters.sort,
      city: city.value?.city,
      page: page.value,
      page_size: 12,
    })
    items.value = reset ? data.items : [...items.value, ...data.items]
    total.value = data.total
    pages.value = data.pages
  } catch (error) {
    ui.error(error.message)
    if (reset) items.value = []
  } finally {
    loading.value = false
  }
}

function syncUrl() {
  const query = {}
  if (!props.fixedType && filters.type) query.tipo = filters.type
  if (filters.species) query.especie = filters.species
  if (filters.q) query.q = filters.q
  if (city.value?.city) query.ciudad = city.value.city
  router.replace({ query })
}

async function loadMore() {
  page.value += 1
  await load(false)
}

function resetFilters() {
  filters.type = props.fixedType || ''
  filters.species = ''
  filters.q = ''
  filters.sex = ''
  filters.breed = ''
  filters.color = ''
  filters.date_from = ''
  filters.include_resolved = false
  city.value = null
  load()
}

watch(city, (value) => {
  if (value) ui.setCity(value)
  syncUrl()
  load()
})

watch(
  () => [filters.type, filters.species, filters.sex, filters.include_resolved, filters.sort, filters.date_from],
  () => {
    syncUrl()
    load()
  },
)

let searchTimer = null
watch(
  () => [filters.q, filters.breed, filters.color],
  () => {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(() => {
      syncUrl()
      load()
    }, 400)
  },
)

onMounted(load)
</script>

<template>
  <div class="container section">
    <h1>{{ title }}</h1>
    <p class="text-soft intro">
      Filtra por ciudad para encontrar mascotas cerca de ti. Puedes buscar por nombre, raza o color.
    </p>

    <!-- Filtros -->
    <div class="filters panel">
      <div class="field">
        <label class="label" for="q">Buscar</label>
        <input
          id="q"
          v-model="filters.q"
          class="input"
          type="search"
          placeholder="Nombre, raza, color o barrio"
        />
      </div>

      <div class="field">
        <span class="label">📍 Ciudad</span>
        <CitySelect v-model="city" allow-clear placeholder="Todas las ciudades" />
      </div>

      <div v-if="!fixedType" class="field">
        <span class="label">Tipo de publicación</span>
        <div class="chip-group">
          <button
            v-for="tipo in TIPOS"
            :key="tipo.value"
            type="button"
            class="chip"
            :class="{ 'is-selected': filters.type === tipo.value }"
            @click="filters.type = tipo.value"
          >
            {{ tipo.emoji }} {{ tipo.label }}
          </button>
        </div>
      </div>

      <div class="field">
        <span class="label">Especie</span>
        <div class="chip-group">
          <button
            v-for="especie in ESPECIES"
            :key="especie.value"
            type="button"
            class="chip"
            :class="{ 'is-selected': filters.species === especie.value }"
            @click="filters.species = especie.value"
          >
            {{ especie.label }}
          </button>
        </div>
      </div>

      <!-- Antes estaban plegados tras un botón «+ Más filtros». Se muestran
           siempre: esconderlos hacía que casi nadie los descubriera. -->
      <div class="form-grid cols-2 advanced">
        <div class="field">
          <label class="label" for="breed">Raza</label>
          <input id="breed" v-model="filters.breed" class="input" type="text" placeholder="Ej.: criollo" />
        </div>
        <div class="field">
          <label class="label" for="color">Color</label>
          <input id="color" v-model="filters.color" class="input" type="text" placeholder="Ej.: negro" />
        </div>
        <div class="field">
          <label class="label" for="sex">Sexo</label>
          <select id="sex" v-model="filters.sex" class="select">
            <option value="">Cualquiera</option>
            <option value="macho">Macho</option>
            <option value="hembra">Hembra</option>
            <option value="desconocido">No se sabe</option>
          </select>
        </div>
        <div class="field">
          <label class="label" for="date_from">Desde la fecha</label>
          <input id="date_from" v-model="filters.date_from" class="input" type="date" />
        </div>
        <div class="field">
          <label class="label" for="sort">Ordenar por</label>
          <select id="sort" v-model="filters.sort" class="select">
            <option value="recientes">Más recientes</option>
            <option value="evento">Fecha del evento</option>
            <option value="antiguas">Más antiguas</option>
          </select>
        </div>
        <div class="field field-full">
          <label class="switch-row">
            <span>Incluir casos ya resueltos o cerrados</span>
            <input v-model="filters.include_resolved" type="checkbox" />
          </label>
        </div>
      </div>
    </div>

    <!-- Resultados -->
    <div class="results-head">
      <p class="text-soft">
        <strong>{{ total }}</strong>
        {{ total === 1 ? 'publicación encontrada' : 'publicaciones encontradas' }}
      </p>
      <div class="row-tight">
        <span v-for="chip in activeFilters" :key="chip" class="badge badge-neutral">{{ chip }}</span>
        <button v-if="activeFilters.length" class="btn btn-quiet btn-sm" type="button" @click="resetFilters">
          Limpiar filtros
        </button>
      </div>
    </div>

    <div v-if="loading && !items.length" class="pet-grid">
      <div v-for="n in 8" :key="n" class="skeleton card-skeleton"></div>
    </div>

    <div v-else-if="items.length" class="pet-grid stagger">
      <!-- El escalonado se reinicia por página: `index % 8` evita que la fila 40
           de una búsqueda larga espere segundos antes de aparecer. -->
      <PetCard
        v-for="(post, index) in items"
        :key="post.id"
        :post="post"
        :style="{ '--i': index % 8 }"
      />
    </div>

    <EmptyState
      v-else
      emoji="🔍"
      title="No encontramos mascotas con esos filtros"
      message="Prueba quitando algún filtro o buscando en otra ciudad. También puedes revisar los casos ya resueltos."
    >
      <button class="btn btn-ghost" type="button" @click="resetFilters">Limpiar filtros</button>
    </EmptyState>

    <div v-if="page < pages" class="load-more">
      <button class="btn btn-ghost btn-lg" type="button" :disabled="loading" @click="loadMore">
        {{ loading ? 'Cargando…' : 'Ver más publicaciones' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.intro { margin-top: -6px; max-width: 60ch; }

.filters { margin-bottom: 20px; }
.filters .field:last-of-type { margin-bottom: 0; }

.advanced { margin-top: 12px; border-top: 1px dashed var(--border); padding-top: 14px; }

.results-head {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;
}
.results-head p { margin: 0; }

.card-skeleton { height: 300px; }

.load-more {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

@media (min-width: 768px) {
  .results-head {
    grid-template-columns: auto 1fr;
    align-items: center;
    gap: 16px;
  }
}
</style>
