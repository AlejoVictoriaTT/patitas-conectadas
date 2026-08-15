<script setup>
import { computed, onMounted, ref } from 'vue'
import StatusBadge from '@/components/StatusBadge.vue'
import EmptyState from '@/components/EmptyState.vue'
import { api } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { formatShortDate, postTitle, typeMeta } from '@/lib/format'
import { setPageTitle } from '@/lib/head'

const ui = useUiStore()
const posts = ref([])
const loading = ref(true)
const filter = ref('activas')

const activas = computed(() => posts.value.filter((p) => !p.is_resolved && p.is_active))
const cerradas = computed(() => posts.value.filter((p) => p.is_resolved || !p.is_active))
const visibles = computed(() => (filter.value === 'activas' ? activas.value : cerradas.value))

onMounted(async () => {
  setPageTitle('Mis publicaciones')
  try {
    posts.value = await api.myPosts()
  } catch (error) {
    ui.error(error.message)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="container section">
    <header class="head">
      <div>
        <h1>Mis publicaciones</h1>
        <p class="text-soft">Edita, cambia el estado o cierra tus publicaciones.</p>
      </div>
      <router-link class="btn btn-primary" to="/publicar">🐾 Publicar</router-link>
    </header>

    <!-- Publicaciones creadas como invitado en este dispositivo -->
    <section v-if="ui.guestPosts.length" class="panel guest-box">
      <h2>Publicaciones de este dispositivo</h2>
      <p class="text-soft small">
        Las creaste como invitado. Vincúlalas a tu cuenta para tenerlas siempre a la mano.
      </p>
      <ul class="guest-list">
        <li v-for="item in ui.guestPosts" :key="item.token">
          <span>{{ typeMeta(item.type).emoji }} {{ item.name }}</span>
          <router-link class="btn btn-ghost btn-sm" :to="`/gestionar/${item.token}`">Administrar</router-link>
        </li>
      </ul>
    </section>

    <div class="chip-group tabs">
      <button
        type="button"
        class="chip"
        :class="{ 'is-selected': filter === 'activas' }"
        @click="filter = 'activas'"
      >
        Activas ({{ activas.length }})
      </button>
      <button
        type="button"
        class="chip"
        :class="{ 'is-selected': filter === 'cerradas' }"
        @click="filter = 'cerradas'"
      >
        Cerradas y resueltas ({{ cerradas.length }})
      </button>
    </div>

    <p v-if="loading" class="text-soft">Cargando…</p>

    <ul v-else-if="visibles.length" class="post-list">
      <li v-for="post in visibles" :key="post.id" class="panel post-row">
        <img v-if="post.photo_url" :src="post.photo_url" :alt="`Foto de ${postTitle(post)}`" />
        <div class="post-info">
          <h3>{{ postTitle(post) }}</h3>
          <div class="row-tight">
            <StatusBadge :post="post" variant="type" />
            <StatusBadge :post="post" />
            <span v-if="!post.is_active" class="badge badge-cerrada">Oculta</span>
          </div>
          <p class="text-muted">
            📍 {{ post.city }} · 📅 {{ formatShortDate(post.event_date) }} · 👁️ {{ post.views }}
          </p>
        </div>
        <div class="post-actions">
          <router-link class="btn btn-ghost btn-sm" :to="post.url">Ver</router-link>
          <router-link class="btn btn-primary btn-sm" :to="`/publicacion/${post.id}/editar`">Administrar</router-link>
        </div>
      </li>
    </ul>

    <EmptyState
      v-else
      title="No tienes publicaciones aquí"
      message="Cuando publiques una mascota aparecerá en esta lista."
    >
      <router-link class="btn btn-primary" to="/publicar">Publicar una mascota</router-link>
    </EmptyState>
  </div>
</template>

<style scoped>
.head {
  display: grid;
  gap: 10px;
  margin-bottom: 18px;
}
.head h1 { margin-bottom: 2px; }
.head p { margin: 0; }

.guest-box { margin-bottom: 18px; }
.guest-box h2 { font-size: 1rem; margin-top: 0; }

.guest-list {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.guest-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  background: var(--surface-2);
  border-radius: var(--radius-sm);
  font-weight: 600;
}

.tabs { margin-bottom: 16px; }

.post-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.post-row {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 12px;
  align-items: center;
}
.post-row img { width: 72px; height: 72px; object-fit: cover; border-radius: var(--radius); }
.post-info h3 { margin: 0 0 6px; font-size: 1.02rem; }
.post-info p { margin: 6px 0 0; }

.post-actions {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

@media (min-width: 768px) {
  .head { grid-template-columns: 1fr auto; align-items: center; }
  .post-row { grid-template-columns: 84px 1fr auto; }
  .post-row img { width: 84px; height: 84px; }
  .post-actions { grid-column: auto; grid-template-columns: auto auto; }
}
</style>
