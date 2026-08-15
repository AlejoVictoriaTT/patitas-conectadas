<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import ShareButtons from '@/components/ShareButtons.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import ReportDialog from '@/components/ReportDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import PhotoSlider from '@/components/PhotoSlider.vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { eventDateLabel, formatDate, postTitle, speciesEmoji, timeAgo, typeMeta } from '@/lib/format'
import { setPageDescription, setPageTitle } from '@/lib/head'

const props = defineProps({
  slug: { type: String, required: true },
  type: { type: String, default: '' },
})

const route = useRoute()
const auth = useAuthStore()

const post = ref(null)
const loading = ref(true)
const notFound = ref(false)
const activePhoto = ref(0)
const showReport = ref(false)
const slider = ref(null)

/** Las miniaturas mueven el carrusel; el carrusel actualiza `activePhoto`. */
function verFoto(index) {
  slider.value?.irA(index)
}

const meta = computed(() => (post.value ? typeMeta(post.value.type) : null))
const title = computed(() => postTitle(post.value))
const shareUrl = computed(() => (post.value ? `${window.location.origin}${post.value.url}` : ''))
const manageToken = computed(() => route.query.token || '')

const detalles = computed(() => {
  if (!post.value) return []
  const p = post.value
  return [
    ['Especie', p.species_label],
    ['Raza', p.breed],
    ['Sexo', p.sex === 'macho' ? 'Macho' : p.sex === 'hembra' ? 'Hembra' : null],
    ['Edad aproximada', p.age],
    ['Color', p.color],
    ['Tamaño', { pequeno: 'Pequeño', mediano: 'Mediano', grande: 'Grande' }[p.size]],
    ['Collar', p.has_collar === null ? null : p.has_collar ? 'Sí' : 'No'],
    ['Placa', p.has_tag === null ? null : p.has_tag ? 'Sí' : 'No'],
    ['Características', p.special_marks],
  ].filter(([, value]) => Boolean(value))
})

async function load() {
  loading.value = true
  notFound.value = false
  try {
    post.value = await api.getPost(props.slug, manageToken.value || undefined)
    activePhoto.value = Math.max(
      0,
      post.value.photos.findIndex((photo) => photo.is_primary),
    )
    setPageTitle(`${meta.value.emoji} ${title.value} — ${post.value.type_label} en ${post.value.city}`)
    setPageDescription(post.value.description)
  } catch (error) {
    if (error.status === 404) notFound.value = true
    post.value = null
  } finally {
    loading.value = false
  }
}

watch(() => props.slug, load, { immediate: true })
</script>

<template>
  <div class="container section">
    <div v-if="loading" class="loading-grid">
      <div class="skeleton photo-skeleton"></div>
      <div class="stack">
        <div class="skeleton line lg"></div>
        <div class="skeleton line"></div>
        <div class="skeleton line"></div>
      </div>
    </div>

    <EmptyState
      v-else-if="notFound || !post"
      emoji="🐾"
      title="No encontramos esta publicación"
      message="Puede que haya sido eliminada o que el enlace esté incompleto."
    >
      <router-link class="btn btn-primary" to="/buscar">Buscar mascotas</router-link>
    </EmptyState>

    <article v-else class="detail">
      <!-- Galería -->
      <div class="gallery">
        <PhotoSlider
          v-if="post.photos.length"
          ref="slider"
          :photos="post.photos"
          :alt="`Foto de ${title}`"
          :start-index="activePhoto"
          :muted="post.is_resolved"
          @update:index="activePhoto = $event"
        >
          <template #overlay>
            <span class="type-tag" :class="`badge-${meta.color}`">
              {{ meta.emoji }} {{ post.type_label }}
            </span>
          </template>
        </PhotoSlider>

        <div v-else class="main-photo">
          <div class="photo-fallback" aria-hidden="true">🐾</div>
          <span class="type-tag" :class="`badge-${meta.color}`">{{ meta.emoji }} {{ post.type_label }}</span>
        </div>

        <div v-if="post.photos.length > 1" class="thumbs" role="tablist" aria-label="Fotos de la mascota">
          <button
            v-for="(photo, index) in post.photos"
            :key="photo.id"
            type="button"
            role="tab"
            :aria-selected="index === activePhoto"
            :aria-label="`Ver foto ${index + 1}`"
            :class="{ 'is-active': index === activePhoto }"
            @click="verFoto(index)"
          >
            <img :src="photo.url" :alt="`Foto ${index + 1}`" loading="lazy" />
          </button>
        </div>
      </div>

      <!-- Información -->
      <div class="info">
        <div v-if="post.is_resolved" class="alert alert-success resolved-banner">
          {{ meta.resolvedMessage }}
        </div>

        <div v-if="!post.is_active" class="alert alert-error">
          Esta publicación está oculta y no aparece en las búsquedas.
        </div>

        <h1>
          <span aria-hidden="true">{{ speciesEmoji(post.species) }}</span>
          {{ title }}
        </h1>

        <div class="row-tight">
          <StatusBadge :post="post" />
          <span class="badge badge-neutral">📍 {{ post.city }}<template v-if="post.neighborhood"> · {{ post.neighborhood }}</template></span>
        </div>

        <ul class="dates">
          <li>
            <strong>{{ eventDateLabel(post) }}</strong>
            {{ formatDate(post.event_date) }}
          </li>
          <li><strong>Publicado:</strong> {{ timeAgo(post.created_at) }}</li>
        </ul>

        <p class="description">{{ post.description }}</p>

        <!-- Contacto -->
        <section class="contact panel">
          <h2>Contacto</h2>
          <p v-if="post.contact.name" class="text-soft">Publicado por {{ post.contact.name }}</p>

          <a
            v-if="post.contact.whatsapp_link"
            class="btn btn-whatsapp btn-lg btn-block"
            :href="post.contact.whatsapp_link"
            target="_blank"
            rel="noopener"
          >
            💬 Contactar por WhatsApp
          </a>

          <div class="contact-links">
            <a v-if="post.contact.phone" class="btn btn-ghost" :href="`tel:${post.contact.phone}`">
              📞 {{ post.contact.phone }}
            </a>
            <a v-if="post.contact.email" class="btn btn-ghost" :href="`mailto:${post.contact.email}`">
              ✉️ Escribir por correo
            </a>
          </div>

          <p v-if="post.contact.note" class="text-muted">🕑 {{ post.contact.note }}</p>
          <p v-if="post.location.address" class="text-muted">🔒 Dirección privada: {{ post.location.address }}</p>
        </section>

        <!-- Datos -->
        <section v-if="detalles.length" class="panel">
          <h2>Datos de la mascota</h2>
          <dl class="facts">
            <div v-for="[etiqueta, valor] in detalles" :key="etiqueta">
              <dt>{{ etiqueta }}</dt>
              <dd>{{ valor }}</dd>
            </div>
          </dl>
        </section>

        <!-- Compartir -->
        <section class="panel">
          <h2>📤 Compartir</h2>
          <p class="text-soft small">
            Compartir esta publicación multiplica las posibilidades de que alguien la reconozca.
          </p>
          <ShareButtons
            :url="shareUrl"
            :title="`${meta.emoji} ${title} — ${post.type_label} en ${post.city}`"
          />
        </section>

        <div class="row footer-actions">
          <router-link
            v-if="post.is_owner"
            class="btn btn-ghost btn-sm"
            :to="manageToken ? `/gestionar/${manageToken}` : `/publicacion/${post.id}/editar`"
          >
            ✏️ Administrar publicación
          </router-link>
          <button class="btn btn-quiet btn-sm" type="button" @click="showReport = true">
            ⚠️ Reportar publicación
          </button>
        </div>
      </div>
    </article>

    <ReportDialog v-if="showReport && post" :identifier="post.public_id" @close="showReport = false" />
  </div>
</template>

<style scoped>
.detail { display: grid; gap: 20px; }

/* Solo se usa cuando la publicación no tiene ninguna foto. */
.main-photo {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--surface-2);
  aspect-ratio: 4 / 3;
}

.photo-fallback { display: grid; place-items: center; height: 100%; font-size: 3rem; opacity: 0.4; }

.type-tag {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 2;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  font-weight: 700;
  font-size: 0.85rem;
  box-shadow: var(--shadow-sm);
}

.thumbs {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-top: 8px;
}
.thumbs button {
  padding: 0;
  border: 2px solid transparent;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: none;
  cursor: pointer;
  aspect-ratio: 1;
  opacity: 0.6;
  transition:
    opacity var(--dur) var(--ease-out),
    border-color var(--dur) var(--ease-out),
    transform var(--dur-fast) var(--ease-out);
}
.thumbs button:hover { opacity: 1; transform: translateY(-2px); }
.thumbs button.is-active { border-color: var(--brand); opacity: 1; }

/* `contain` en vez de `cover`: la miniatura muestra la foto completa encajada
   en su cuadro, no un recorte del centro. Con `cover` una foto vertical se
   quedaba en la franja central y no se reconocía qué mascota era. El fondo
   rellena lo que sobra a los lados. */
.thumbs img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: var(--surface-2);
}

.info { display: grid; gap: 14px; align-content: start; }
.info h1 { margin: 0; }

.resolved-banner { font-weight: 600; }

.dates {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
  color: var(--text-soft);
  font-size: 0.95rem;
}

.description { white-space: pre-line; margin: 0; }

.contact h2,
.panel h2 { font-size: 1.05rem; margin-top: 0; }

.contact { display: grid; gap: 10px; }
.contact p { margin: 0; }

.contact-links { display: grid; gap: 8px; }

.facts { display: grid; gap: 10px; margin: 0; }
.facts > div { display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px dashed var(--border); padding-bottom: 6px; }
.facts > div:last-child { border-bottom: none; padding-bottom: 0; }
.facts dt { color: var(--text-soft); }
.facts dd { margin: 0; font-weight: 600; text-align: right; }

.footer-actions { justify-content: space-between; }

.loading-grid { display: grid; gap: 16px; }
.photo-skeleton { aspect-ratio: 4 / 3; }
.line { height: 18px; }
.line.lg { height: 30px; width: 60%; }

@media (min-width: 480px) {
  .contact-links { grid-template-columns: 1fr 1fr; }
}

@media (min-width: 900px) {
  .detail { grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); gap: 32px; align-items: start; }
  .loading-grid { grid-template-columns: 1fr 1fr; }
  .gallery { position: sticky; top: calc(var(--header-h) + 16px); }
}
</style>
