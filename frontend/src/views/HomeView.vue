<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import CitySelect from '@/components/CitySelect.vue'
import PetCard from '@/components/PetCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import { api } from '@/api/client'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const posts = ref([])
const loading = ref(true)
const stats = ref({ ciudades: 0 })

const city = computed({
  get: () => ui.city,
  set: (value) => ui.setCity(value),
})

async function loadRecent() {
  loading.value = true
  try {
    posts.value = (await api.listPosts({ page_size: 8, city: ui.city?.city })).items
  } catch {
    posts.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadRecent()
  try {
    stats.value.ciudades = (await api.postsCities()).length
  } catch {
    /* opcional */
  }
})

watch(() => ui.city?.city, loadRecent)
</script>

<template>
  <div>
    <!-- Portada -->
    <section class="hero">
      <div class="container hero-inner">
        <p class="eyebrow">🐾 Patitas Conectadas</p>
        <h1>Reencuentros, rescates y nuevos comienzos</h1>
        <p class="lead">
          Publica una mascota perdida, encontrada o en adopción en menos de dos minutos.
          Sin formularios largos y sin necesidad de crear una cuenta.
        </p>

        <div class="actions stagger">
          <router-link
            class="action action-perdida"
            :style="{ '--i': 0 }"
            :to="{ path: '/publicar', query: { tipo: 'perdida' } }"
          >
            <span class="action-emoji" aria-hidden="true">🔴</span>
            <span>
              <strong>Perdí una mascota</strong>
              <small>Publica para que la comunidad la busque contigo</small>
            </span>
          </router-link>

          <router-link
            class="action action-encontrada"
            :style="{ '--i': 1 }"
            :to="{ path: '/publicar', query: { tipo: 'encontrada' } }"
          >
            <span class="action-emoji" aria-hidden="true">🟢</span>
            <span>
              <strong>Encontré una mascota</strong>
              <small>Ayúdala a reencontrarse con su familia</small>
            </span>
          </router-link>

          <router-link class="action action-adopcion" :style="{ '--i': 2 }" to="/adopciones">
            <span class="action-emoji" aria-hidden="true">💙</span>
            <span>
              <strong>Quiero adoptar</strong>
              <small>Conoce mascotas que buscan un hogar</small>
            </span>
          </router-link>

          <router-link class="action action-buscar" :style="{ '--i': 3 }" to="/buscar">
            <span class="action-emoji" aria-hidden="true">🔎</span>
            <span>
              <strong>Buscar mascotas</strong>
              <small>Filtra por ciudad, especie y fecha</small>
            </span>
          </router-link>
        </div>

        <router-link class="btn btn-primary btn-lg btn-block publish-main" to="/publicar">
          🐾 Publicar una mascota
        </router-link>
      </div>
    </section>

    <!-- Ciudad + recientes -->
    <section class="section">
      <div class="container">
        <div v-reveal class="city-bar panel">
          <div>
            <h2 class="city-title">📍 Selecciona tu ciudad</h2>
            <p class="text-muted">
              Verás primero las mascotas publicadas cerca de ti.
              <template v-if="stats.ciudades">Ya hay publicaciones en {{ stats.ciudades }} ciudades.</template>
            </p>
          </div>
          <CitySelect v-model="city" allow-clear placeholder="Todas las ciudades" />
        </div>

        <div class="section-head">
          <h2>🐾 Mascotas recientes</h2>
          <router-link class="btn btn-quiet btn-sm" to="/buscar">Ver todas →</router-link>
        </div>

        <div v-if="loading" class="pet-grid">
          <div v-for="n in 4" :key="n" class="skeleton card-skeleton"></div>
        </div>

        <div v-else-if="posts.length" class="pet-grid stagger">
          <PetCard
            v-for="(post, index) in posts"
            :key="post.id"
            :post="post"
            :style="{ '--i': index }"
          />
        </div>

        <EmptyState
          v-else
          title="Todavía no hay publicaciones aquí"
          :message="
            ui.city
              ? `Aún no hay mascotas publicadas en ${ui.city.city}. Puedes ser la primera persona en publicar.`
              : 'Sé la primera persona en publicar y ayuda a que esta comunidad crezca.'
          "
        >
          <router-link class="btn btn-primary" to="/publicar">Publicar una mascota</router-link>
        </EmptyState>
      </div>
    </section>

    <!-- Ayuda -->
    <section class="section help">
      <div class="container">
        <div class="help-grid">
          <article v-reveal="{ delay: 0 }" class="panel">
            <h3>¿Perdiste a tu mascota?</h3>
            <p class="text-soft">
              Las primeras horas son decisivas. Publica con una foto clara, comparte el enlace por
              WhatsApp y avisa en tu barrio.
            </p>
            <router-link class="btn btn-ghost btn-sm" to="/guias">Ver la guía</router-link>
          </article>

          <article v-reveal="{ delay: 90 }" class="panel">
            <h3>¿Encontraste una mascota?</h3>
            <p class="text-soft">
              Revisa si tiene placa o microchip, tómale una foto y publícala indicando el sector
              donde la viste.
            </p>
            <router-link class="btn btn-ghost btn-sm" :to="{ path: '/publicar', query: { tipo: 'encontrada' } }">
              Publicar ahora
            </router-link>
          </article>

          <article v-reveal="{ delay: 180 }" class="panel">
            <h3>Emergencia y actualidad</h3>
            <p class="text-soft">
              Teléfonos de emergencia y enlaces oficiales de gobernaciones y alcaldías, junto con lo
              que están publicando los medios sobre el terremoto.
            </p>
            <div class="row-tight">
              <router-link class="btn btn-ghost btn-sm" to="/emergencia">Teléfonos</router-link>
              <router-link class="btn btn-quiet btn-sm" to="/noticias">Noticias</router-link>
            </div>
          </article>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero {
  position: relative;
  background:
    radial-gradient(1200px 320px at 15% -10%, var(--brand-light), transparent 70%),
    radial-gradient(900px 260px at 92% 0%, var(--accent-soft), transparent 72%),
    linear-gradient(180deg, var(--accent-soft) 0%, var(--bg) 65%);
  padding: 24px 0 8px;
  overflow: hidden;
}

.hero-inner { display: grid; gap: 14px; }

/* Entrada en cascada de la portada: cada pieza entra un poco después que la
   anterior. Es lo primero que ve el usuario, así que marca el tono. */
@keyframes hero-in {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.eyebrow,
.hero h1,
.lead,
.publish-main {
  animation: hero-in 0.7s var(--ease-out) both;
}

.eyebrow { animation-delay: 0.02s; }
.hero h1 { animation-delay: 0.1s; }
.lead { animation-delay: 0.18s; }
.publish-main { animation-delay: 0.5s; }

/* Las cuatro tarjetas de acción entran en cascada (clase `stagger`), empezando
   después del texto de la portada. */
.actions { --stagger-step: 70ms; }
.actions > * { animation-delay: calc(0.26s + var(--stagger-step) * var(--i, 0)); }

.eyebrow {
  margin: 0;
  font-weight: 700;
  color: var(--brand);
  letter-spacing: 0.02em;
}

.hero h1 { margin: 0; }

.lead {
  margin: 0;
  color: var(--text-soft);
  font-size: 1.02rem;
  max-width: 56ch;
}

.actions {
  display: grid;
  gap: 10px;
  margin-top: 6px;
}

.action {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  min-height: 72px;
  border-radius: var(--radius-lg);
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  box-shadow: var(--shadow-sm);
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.action:hover {
  text-decoration: none;
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.action span { display: grid; gap: 2px; }
.action strong { font-size: 1.02rem; }
.action small { color: var(--text-soft); font-size: 0.85rem; }
.action-emoji { font-size: 1.6rem; display: block; flex: none; }

.action-perdida { border-left: 5px solid var(--perdida); }
.action-encontrada { border-left: 5px solid var(--encontrada); }
.action-adopcion { border-left: 5px solid var(--adopcion); }
.action-buscar { border-left: 5px solid var(--brand); }

.publish-main { margin-top: 4px; }

.city-bar {
  display: grid;
  gap: 12px;
  margin-bottom: 22px;
}

.city-title { margin: 0 0 2px; font-size: 1.1rem; }
.city-bar p { margin: 0; }

.card-skeleton { height: 300px; }

.help-grid { display: grid; gap: 14px; }
.help-grid h3 { margin-top: 0; }
.help-grid p { font-size: 0.95rem; }

@media (min-width: 480px) {
  .actions { grid-template-columns: 1fr 1fr; }
}

@media (min-width: 768px) {
  .hero { padding: 44px 0 20px; }
  .lead { font-size: 1.12rem; }
  .publish-main { justify-self: start; width: auto; padding-inline: 40px; }
  .city-bar { grid-template-columns: 1fr minmax(260px, 340px); align-items: center; }
  .help-grid { grid-template-columns: repeat(3, 1fr); }
}

@media (min-width: 1024px) {
  .actions { grid-template-columns: repeat(4, 1fr); }
  .action { flex-direction: column; align-items: flex-start; min-height: 128px; }
}
</style>
