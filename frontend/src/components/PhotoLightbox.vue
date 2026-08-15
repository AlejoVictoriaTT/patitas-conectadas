<script setup>
/**
 * Visor a pantalla completa, al estilo de Facebook.
 *
 * La foto se ve entera y lo más grande que quepa: `object-fit: contain` contra
 * el viewport completo. Nunca recorta, que es justamente lo que se le pide a un
 * visor — para eso ya está la tarjeta con su encuadre.
 *
 * Detalles de accesibilidad que importan aquí:
 *  - Se bloquea el scroll del fondo mientras está abierto, si no la página de
 *    atrás se mueve al deslizar sobre la foto.
 *  - El foco se lleva al botón de cerrar al abrir y se devuelve al elemento que
 *    lo abrió al cerrar, para no perder el sitio si se navega con teclado.
 *  - Escape cierra; las flechas cambian de foto.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  photos: { type: Array, default: () => [] },
  index: { type: Number, default: 0 },
  alt: { type: String, default: 'Foto de la mascota' },
})

const emit = defineEmits(['close', 'update:index'])

const actual = ref(props.index)
const closeBtn = ref(null)
const total = computed(() => props.photos.length)
const hasMultiple = computed(() => total.value > 1)
const foto = computed(() => props.photos[actual.value])

let focoPrevio = null
let scrollBloqueado = false

function irA(destino) {
  if (!total.value) return
  // Da la vuelta: desde la última, «siguiente» lleva a la primera.
  actual.value = (destino + total.value) % total.value
  emit('update:index', actual.value)
}

const anterior = () => irA(actual.value - 1)
const siguiente = () => irA(actual.value + 1)

function cerrar() {
  emit('close')
}

function alTeclado(evento) {
  if (evento.key === 'Escape') {
    evento.preventDefault()
    cerrar()
  } else if (evento.key === 'ArrowLeft' && hasMultiple.value) {
    evento.preventDefault()
    anterior()
  } else if (evento.key === 'ArrowRight' && hasMultiple.value) {
    evento.preventDefault()
    siguiente()
  }
}

// Deslizar con el dedo para cambiar de foto.
let inicioX = null
function alTocar(evento) {
  inicioX = evento.changedTouches[0].clientX
}
function alSoltar(evento) {
  if (inicioX === null) return
  const recorrido = evento.changedTouches[0].clientX - inicioX
  inicioX = null
  if (Math.abs(recorrido) < 50 || !hasMultiple.value) return
  recorrido > 0 ? anterior() : siguiente()
}

function bloquearScroll(bloquear) {
  if (bloquear === scrollBloqueado) return
  document.body.style.overflow = bloquear ? 'hidden' : ''
  scrollBloqueado = bloquear
}

watch(
  () => props.index,
  (valor) => {
    actual.value = valor
  },
)

// El visor se monta solo cuando se abre (v-if en el padre), así que el montaje
// es el momento de preparar el entorno y el desmontaje el de deshacerlo.
onMounted(async () => {
  focoPrevio = document.activeElement
  bloquearScroll(true)
  document.addEventListener('keydown', alTeclado)
  await nextTick()
  closeBtn.value?.focus()
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', alTeclado)
  bloquearScroll(false)
  focoPrevio?.focus?.()
})
</script>

<template>
  <div
    class="lightbox"
    role="dialog"
    aria-modal="true"
    :aria-label="`Foto ${actual + 1} de ${total}`"
    @click.self="cerrar"
  >
    <div class="bar">
      <span v-if="hasMultiple" class="counter">{{ actual + 1 }} / {{ total }}</span>
      <span v-else></span>
      <button ref="closeBtn" type="button" class="icon-btn" aria-label="Cerrar" @click="cerrar">
        <span aria-hidden="true">✕</span>
      </button>
    </div>

    <!-- El clic en el hueco alrededor de la foto también cierra. -->
    <div class="stage" @click.self="cerrar" @touchstart.passive="alTocar" @touchend.passive="alSoltar">
      <img v-if="foto" :src="foto.url" :alt="`${alt} (${actual + 1} de ${total})`" decoding="async" />
    </div>

    <template v-if="hasMultiple">
      <button type="button" class="nav nav-prev" aria-label="Foto anterior" @click="anterior">
        <span aria-hidden="true">‹</span>
      </button>
      <button type="button" class="nav nav-next" aria-label="Foto siguiente" @click="siguiente">
        <span aria-hidden="true">›</span>
      </button>

      <div class="strip">
        <button
          v-for="(photo, i) in photos"
          :key="photo.id"
          type="button"
          class="thumb"
          :class="{ 'is-active': i === actual }"
          :aria-label="`Ver foto ${i + 1}`"
          @click="irA(i)"
        >
          <img :src="photo.url" :alt="`Miniatura ${i + 1}`" loading="lazy" />
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  flex-direction: column;
  background: rgba(10, 14, 18, 0.94);
  animation: lightbox-in 0.22s var(--ease-out) both;
}

@keyframes lightbox-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px calc(10px + env(safe-area-inset-top, 0px));
  flex: none;
}

.counter {
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.88rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  padding-inline: 6px;
}

.icon-btn {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 1.3rem;
  cursor: pointer;
  transition: background var(--dur) var(--ease-out);
}
.icon-btn:hover { background: rgba(255, 255, 255, 0.24); }

/*
  El escenario ocupa todo el alto que sobra y la foto se ajusta dentro con
  `contain`: se ve completa y tan grande como quepa, sin recortes ni zoom.
  `min-height: 0` es lo que permite que este hijo flexible pueda encogerse;
  sin él, una foto alta empujaría la tira de miniaturas fuera de la pantalla.
*/
.stage {
  flex: 1;
  min-height: 0;
  display: grid;
  place-items: center;
  padding: 0 12px;
}

.stage img {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
  border-radius: var(--radius-sm);
}

.nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  font-size: 2rem;
  line-height: 1;
  padding-bottom: 5px;
  cursor: pointer;
  transition:
    background var(--dur) var(--ease-out),
    transform var(--dur) var(--ease-out);
}
.nav:hover {
  background: rgba(255, 255, 255, 0.28);
  transform: translateY(-50%) scale(1.06);
}

.nav-prev { left: 10px; }
.nav-next { right: 10px; }

.strip {
  flex: none;
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 12px calc(12px + env(safe-area-inset-bottom, 0px));
  overflow-x: auto;
  scrollbar-width: none;
}
.strip::-webkit-scrollbar { display: none; }

.thumb {
  flex: none;
  width: 62px;
  height: 62px;
  padding: 0;
  border: 2px solid transparent;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.08);
  cursor: pointer;
  opacity: 0.55;
  overflow: hidden;
  transition:
    opacity var(--dur) var(--ease-out),
    border-color var(--dur) var(--ease-out);
}
.thumb:hover { opacity: 1; }
.thumb.is-active { opacity: 1; border-color: #fff; }

/* También aquí la miniatura muestra la foto entera, no un recorte del centro. */
.thumb img { width: 100%; height: 100%; object-fit: contain; }

/* En pantallas táctiles se navega deslizando; las flechas estorban. */
@media (hover: none) {
  .nav { display: none; }
}

@media (min-width: 768px) {
  .stage { padding: 0 64px; }
  .thumb { width: 72px; height: 72px; }
}
</style>
