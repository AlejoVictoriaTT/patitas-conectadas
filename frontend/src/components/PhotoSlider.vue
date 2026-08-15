<script setup>
/**
 * Carrusel horizontal de fotos.
 *
 * El desplazamiento lo hace el propio navegador (`scroll-snap`), no JavaScript:
 * así el gesto táctil se siente nativo, la inercia es la del sistema y sigue
 * funcionando aunque el script falle. El JS solo escucha el scroll para saber
 * qué foto está al frente y mueve el carrusel cuando se usan los botones.
 *
 * Las fotos se muestran completas (`object-fit: contain`) sobre un fondo
 * difuminado de la misma imagen, para no recortar a la mascota.
 */
import { computed, nextTick, onBeforeUnmount, onBeforeUpdate, onMounted, ref, watch } from 'vue'
import PhotoLightbox from '@/components/PhotoLightbox.vue'

const props = defineProps({
  photos: { type: Array, default: () => [] },
  alt: { type: String, default: 'Foto de la mascota' },
  startIndex: { type: Number, default: 0 },
  muted: { type: Boolean, default: false }, // publicación ya resuelta
})

// Avisa qué foto está al frente para que las miniaturas se resalten.
const emit = defineEmits(['update:index'])

const track = ref(null)
const active = ref(props.startIndex)
const slides = ref([])

const total = computed(() => props.photos.length)
const hasMultiple = computed(() => total.value > 1)

// Las referencias a los slides se rehacen en cada render para no dejar nodos viejos.
onBeforeUpdate(() => {
  slides.value = []
})

function movimientoReducido() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

function irA(indice, comportamiento = 'smooth') {
  const destino = Math.max(0, Math.min(indice, total.value - 1))
  const slide = slides.value[destino]
  if (!track.value || !slide) return
  const modo = comportamiento === 'smooth' && movimientoReducido() ? 'auto' : comportamiento
  track.value.scrollTo({ left: slide.offsetLeft, behavior: modo })
  active.value = destino
}

function anterior() {
  irA(active.value - 1)
}

function siguiente() {
  irA(active.value + 1)
}

// Al desplazar con el dedo, la foto activa es la más cercana al centro.
let cuadro = null
function alDesplazar() {
  if (cuadro) return
  cuadro = requestAnimationFrame(() => {
    cuadro = null
    const contenedor = track.value
    if (!contenedor) return
    const centro = contenedor.scrollLeft + contenedor.clientWidth / 2
    let mejor = 0
    let menorDistancia = Infinity
    slides.value.forEach((slide, i) => {
      if (!slide) return
      const distancia = Math.abs(slide.offsetLeft + slide.offsetWidth / 2 - centro)
      if (distancia < menorDistancia) {
        menorDistancia = distancia
        mejor = i
      }
    })
    active.value = mejor
  })
}

// ------------------------------------------------------- pantalla completa

const visorAbierto = ref(false)

function abrirVisor(indice) {
  irA(indice, 'auto')
  visorAbierto.value = true
}

function cerrarVisor() {
  visorAbierto.value = false
}

/** Al cambiar de foto dentro del visor, el carrusel de atrás la sigue: al
 *  cerrar, queda mostrando la misma que se estaba viendo. */
function alCambiarEnVisor(indice) {
  irA(indice, 'auto')
}

function alTeclado(evento) {
  // Con el visor abierto manda él: si no, una flecha movería las dos galerías.
  if (visorAbierto.value || !hasMultiple.value) return
  if (evento.key === 'ArrowLeft') {
    evento.preventDefault()
    anterior()
  } else if (evento.key === 'ArrowRight') {
    evento.preventDefault()
    siguiente()
  }
}

onMounted(async () => {
  await nextTick()
  // Sin animación en el primer posicionamiento: la foto principal ya debe
  // aparecer al frente, no deslizarse hasta ella.
  if (props.startIndex > 0) irA(props.startIndex, 'auto')
})

onBeforeUnmount(() => {
  if (cuadro) cancelAnimationFrame(cuadro)
})

watch(active, (indice) => emit('update:index', indice))

// Si cambia la publicación (o se reordenan las fotos) se vuelve al inicio.
watch(
  () => props.photos.map((p) => p.id).join(','),
  async () => {
    await nextTick()
    irA(props.startIndex, 'auto')
  },
)

defineExpose({ irA })
</script>

<template>
  <div class="slider">
    <div
      ref="track"
      class="track"
      :class="{ 'is-single': !hasMultiple }"
      tabindex="0"
      role="group"
      :aria-label="`Galería de fotos: ${total} ${total === 1 ? 'foto' : 'fotos'}`"
      @scroll.passive="alDesplazar"
      @keydown="alTeclado"
    >
      <figure
        v-for="(photo, index) in photos"
        :key="photo.id"
        :ref="(el) => (slides[index] = el)"
        class="slide"
        :aria-label="`Foto ${index + 1} de ${total}`"
      >
        <!-- Fondo difuminado: rellena el marco sin recortar la foto real. -->
        <div class="slide-bg" :style="{ backgroundImage: `url(${photo.url})` }" aria-hidden="true"></div>
        <img
          :src="photo.url"
          :alt="`${alt} (${index + 1} de ${total})`"
          :class="{ muted }"
          :loading="index === 0 ? 'eager' : 'lazy'"
          decoding="async"
          @click="abrirVisor(index)"
        />
      </figure>
    </div>

    <button
      type="button"
      class="expand"
      aria-label="Ver las fotos en pantalla completa"
      title="Ver en pantalla completa"
      @click="abrirVisor(active)"
    >
      <span aria-hidden="true">⤢</span>
    </button>

    <template v-if="hasMultiple">
      <button
        type="button"
        class="nav nav-prev"
        :disabled="active === 0"
        aria-label="Foto anterior"
        @click="anterior"
      >
        <span aria-hidden="true">‹</span>
      </button>
      <button
        type="button"
        class="nav nav-next"
        :disabled="active === total - 1"
        aria-label="Foto siguiente"
        @click="siguiente"
      >
        <span aria-hidden="true">›</span>
      </button>

      <span class="counter">{{ active + 1 }} / {{ total }}</span>

      <div class="dots" role="tablist" aria-label="Ir a una foto">
        <button
          v-for="(photo, index) in photos"
          :key="photo.id"
          type="button"
          role="tab"
          class="dot-btn"
          :aria-selected="index === active"
          :aria-label="`Ver foto ${index + 1}`"
          :class="{ 'is-active': index === active }"
          @click="irA(index)"
        ></button>
      </div>
    </template>

    <slot name="overlay" />

    <!--
      El visor se teletransporta al <body> a propósito. Aquí dentro quedaría
      atrapado: `.slider` recorta con `overflow: hidden`, y en el detalle la
      galería es `position: sticky`. Cualquier ancestro con `transform` o
      `filter` también convertiría un `position: fixed` en relativo a él y el
      visor dejaría de cubrir la pantalla.
    -->
    <Teleport to="body">
      <PhotoLightbox
        v-if="visorAbierto"
        :photos="photos"
        :index="active"
        :alt="alt"
        @close="cerrarVisor"
        @update:index="alCambiarEnVisor"
      />
    </Teleport>
  </div>
</template>

<style scoped>
.slider {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: #10161d;
  box-shadow: var(--shadow-sm);
}

.track {
  display: flex;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  /* El desplazamiento suave lo pide `scrollTo` en JS, no el CSS: así se puede
     saltar de golpe a la foto principal al abrir la publicación. */
  /* La barra de scroll se oculta: se navega con gestos, flechas o puntos. */
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.track::-webkit-scrollbar { display: none; }
.track:focus-visible { outline-offset: -3px; }

.track.is-single { overflow-x: hidden; }

.slide {
  position: relative;
  flex: 0 0 100%;
  scroll-snap-align: center;
  scroll-snap-stop: always;
  margin: 0;
  aspect-ratio: 4 / 3;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.slide-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: blur(28px) saturate(1.1) brightness(0.6);
  transform: scale(1.15);
}

/*
  La imagen ocupa exactamente la caja del slide y `object-fit: contain` la
  encaja dentro sin recortarla.

  Antes se usaba `max-height: 100%` con alto automático, y ahí estaba el fallo:
  la fila de la rejilla no tenía altura definida, el porcentaje no resolvía
  contra nada y la foto crecía hasta su tamaño natural. El `overflow: hidden`
  del slide se comía el resto, de modo que en las verticales solo se veía la
  mitad de arriba. Con `inset: 0` la altura pasa a ser definida y `contain`
  puede hacer su trabajo.
*/
.slide img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  cursor: zoom-in;
}

.slide img.muted { filter: saturate(0.6); }

/* ------------------------------------------------------------ navegación */

.nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  color: var(--text);
  font-size: 1.9rem;
  line-height: 1;
  padding-bottom: 4px;
  cursor: pointer;
  box-shadow: var(--shadow);
  transition:
    opacity var(--dur) var(--ease-out),
    transform var(--dur) var(--ease-out),
    background var(--dur) var(--ease-out);
}

.nav:hover:not(:disabled) {
  background: #fff;
  transform: translateY(-50%) scale(1.08);
}

.nav:disabled {
  opacity: 0;
  pointer-events: none;
}

.nav-prev { left: 10px; }
.nav-next { right: 10px; }

/* Botón de maximizar, en la esquina opuesta al contador. */
.expand {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 3;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border: none;
  border-radius: 50%;
  background: rgba(16, 22, 29, 0.55);
  color: #fff;
  font-size: 1.05rem;
  cursor: pointer;
  backdrop-filter: blur(4px);
  transition:
    background var(--dur) var(--ease-out),
    transform var(--dur) var(--ease-out);
}
.expand:hover {
  background: rgba(16, 22, 29, 0.8);
  transform: scale(1.08);
}

.counter {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  background: rgba(16, 22, 29, 0.62);
  color: #fff;
  font-size: 0.78rem;
  font-weight: 700;
  backdrop-filter: blur(4px);
}

.dots {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 10px;
  display: flex;
  justify-content: center;
  gap: 7px;
}

.dot-btn {
  width: 8px;
  height: 8px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition:
    width var(--dur) var(--ease-out),
    background var(--dur) var(--ease-out);
}

.dot-btn.is-active {
  width: 22px;
  border-radius: var(--radius-pill);
  background: #fff;
}

/* En pantallas táctiles las flechas estorban: se navega deslizando. */
@media (hover: none) {
  .nav { display: none; }
}

@media (min-width: 768px) {
  .slide { aspect-ratio: 3 / 2; }
}
</style>
