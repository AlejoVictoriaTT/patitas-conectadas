<script setup>
import { computed } from 'vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { formatShortDate, postTitle, speciesEmoji, typeMeta } from '@/lib/format'

const props = defineProps({
  post: { type: Object, required: true },
})

const meta = computed(() => typeMeta(props.post.type))
const title = computed(() => postTitle(props.post))
const location = computed(() =>
  [props.post.city, props.post.neighborhood].filter(Boolean).join(' · '),
)
</script>

<template>
  <article class="pet-card card" :class="{ 'is-resolved': post.is_resolved }">
    <router-link :to="post.url" class="photo-link" :aria-label="`Ver la publicación de ${title}`">
      <div class="photo">
        <img
          v-if="post.photo_url"
          :src="post.photo_url"
          :alt="`Foto de ${title}`"
          loading="lazy"
          decoding="async"
        />
        <div v-else class="photo-fallback" aria-hidden="true">🐾</div>
        <span class="type-tag" :class="`badge-${meta.color}`">{{ meta.emoji }} {{ post.type_label }}</span>
      </div>
    </router-link>

    <div class="card-body">
      <h3 class="title">
        <span class="title-emoji" aria-hidden="true">{{ speciesEmoji(post.species) }}</span>
        <router-link :to="post.url">{{ title }}</router-link>
      </h3>

      <div class="status-row">
        <StatusBadge :post="post" />
      </div>

      <ul class="facts">
        <li><span aria-hidden="true">📍</span> <span class="fact-text">{{ location }}</span></li>
        <li><span aria-hidden="true">📅</span> <span class="fact-text">{{ formatShortDate(post.event_date) }}</span></li>
      </ul>

      <router-link class="btn btn-ghost btn-sm btn-block card-cta" :to="post.url">
        Ver publicación
      </router-link>
    </div>
  </article>
</template>

<style scoped>
/*
  Todas las tarjetas deben medir lo mismo aunque su contenido no lo sea. Para
  lograrlo: la tarjeta ocupa el 100% de la fila del grid (`.pet-grid` reparte
  filas iguales), el cuerpo es una columna flexible, cada texto está limitado a
  una sola línea y el botón se empuja al fondo con `margin-top: auto`.
*/
.pet-card {
  /* Medidas del anclaje del botón, en un solo sitio para que padding y
     posición no se puedan desincronizar. `--card-pad` iguala el padding de
     `.card-body` que define main.css. */
  --card-pad: 16px;
  --card-cta-h: 38px; /* min-height de .btn-sm */
  --card-cta-gap: 10px;

  display: flex;
  flex-direction: column;
  height: 100%;
  transition:
    transform 0.35s var(--ease-out),
    box-shadow 0.35s var(--ease-out),
    border-color 0.35s var(--ease-out);
}

.pet-card:hover,
.pet-card:focus-within {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--brand-light);
}

.photo-link { display: block; }

.photo {
  position: relative;
  aspect-ratio: 4 / 3;
  background: var(--surface-2);
  overflow: hidden;
}

.photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s var(--ease-out);
}

.pet-card:hover .photo img { transform: scale(1.05); }

.photo-fallback {
  display: grid;
  place-items: center;
  height: 100%;
  font-size: 2.5rem;
  opacity: 0.4;
}

.type-tag {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  font-size: 0.78rem;
  font-weight: 700;
  box-shadow: var(--shadow-sm);
}

.is-resolved .photo img { filter: saturate(0.55); }

/*
  El botón va anclado al fondo, no empujado por el contenido.

  Antes se usaba `margin-top: auto`, que depende de que el cuerpo reciba
  espacio sobrante del flex. Cuando el texto de una tarjeta ocupaba justo lo
  mismo que su alto disponible no quedaba sobrante que absorber, y el botón
  terminaba pegado al texto mientras en las tarjetas vecinas quedaba abajo.

  Ahora el botón se posiciona de forma absoluta a una distancia fija del borde
  inferior, y el cuerpo reserva ese espacio con `padding-bottom`. Resultado: en
  todas las tarjetas queda exactamente a la misma altura, mida lo que mida el
  texto de arriba.
*/
.card-body {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 0;
  /* alto del botón (--tap-sm) + separación + margen inferior */
  padding-bottom: calc(var(--card-cta-h) + var(--card-cta-gap) + var(--card-pad));
}

.title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 1.05rem;
  min-width: 0;
}
.title-emoji { flex: none; }
.title a {
  color: var(--text);
  /* Una sola línea: un nombre largo no puede estirar la tarjeta. */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

/* La insignia de estado no envuelve: recorta antes de crecer a dos líneas. */
.status-row {
  display: flex;
  min-width: 0;
  overflow: hidden;
}
.status-row :deep(.badge) {
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.facts {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 3px;
  color: var(--text-soft);
  font-size: 0.9rem;
}

.facts li {
  display: flex;
  gap: 6px;
  align-items: center;
  min-width: 0;
}

.fact-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-cta {
  position: absolute;
  left: var(--card-pad);
  right: var(--card-pad);
  bottom: var(--card-pad);
  min-height: var(--card-cta-h);
  /* `.btn-block` trae `width: 100%`, que al estar posicionado en absoluto se
     mediría contra la caja de relleno del cuerpo e ignoraría el `right`,
     desbordando la tarjeta. Con `auto`, mandan `left` y `right`. */
  width: auto;
}
</style>
