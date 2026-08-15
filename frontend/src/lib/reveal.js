/**
 * Directiva `v-reveal`: aparición suave cuando el elemento entra en pantalla.
 *
 *   <section v-reveal>…</section>
 *   <article v-reveal="{ delay: 120, from: 'left' }">…</article>
 *
 * Principio de diseño: el estado base del CSS es VISIBLE. La directiva es la
 * que oculta al montar y vuelve a mostrar al entrar en pantalla. Así, si el
 * JavaScript no corre, el navegador no soporta IntersectionObserver o el
 * usuario pidió menos movimiento, el contenido se ve igual — nunca se queda
 * una sección en blanco por culpa de una animación.
 */

const REDUCED_MOTION = '(prefers-reduced-motion: reduce)'

// Si por lo que sea el observador nunca dispara, mostramos igual pasado este
// tiempo. Más vale perder la animación que perder el contenido.
const RESCATE_MS = 1500

function prefiereMenosMovimiento() {
  return typeof window !== 'undefined' && window.matchMedia?.(REDUCED_MOTION).matches
}

function mostrar(el) {
  el.classList.remove('is-hidden')
  if (el._revealTimer) {
    clearTimeout(el._revealTimer)
    el._revealTimer = null
  }
  if (el._revealObserver) {
    el._revealObserver.disconnect()
    el._revealObserver = null
  }
}

export const reveal = {
  mounted(el, binding) {
    const opciones = binding.value || {}

    el.classList.add('reveal')
    if (opciones.from === 'left') el.classList.add('reveal-left')
    if (opciones.from === 'right') el.classList.add('reveal-right')
    if (opciones.from === 'zoom') el.classList.add('reveal-zoom')
    if (opciones.delay) el.style.setProperty('--reveal-delay', `${opciones.delay}ms`)

    if (prefiereMenosMovimiento() || typeof IntersectionObserver === 'undefined') {
      return // se queda visible, sin animación
    }

    el.classList.add('is-hidden')

    el._revealObserver = new IntersectionObserver(
      (entradas) => {
        for (const entrada of entradas) {
          if (entrada.isIntersecting) mostrar(el)
        }
      },
      // Un margen inferior negativo hace que la animación arranque cuando el
      // elemento ya subió un poco, no en el instante en que asoma.
      { threshold: opciones.threshold ?? 0.12, rootMargin: '0px 0px -40px 0px' },
    )

    el._revealObserver.observe(el)
    el._revealTimer = setTimeout(() => mostrar(el), RESCATE_MS)
  },

  unmounted(el) {
    if (el._revealTimer) clearTimeout(el._revealTimer)
    el._revealObserver?.disconnect()
    el._revealObserver = null
  },
}

export default reveal
