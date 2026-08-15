<script setup>
// Redes sociales. Para agregar otra basta con sumarla a esta lista: el ícono se
// dibuja en línea (SVG) para no depender de ninguna librería externa.
// Los enlaces del pie duplican lo que ya está en el menú principal, así que por
// ahora se quedan ocultos. Cambiar a `true` los vuelve a mostrar tal cual.
const MOSTRAR_ENLACES = false

const REDES = [
  {
    nombre: 'Instagram',
    url: 'https://www.instagram.com/patitas_conectadas_co/',
    usuario: '@patitas_conectadas_co',
    icono:
      'M12 2.16c3.2 0 3.58.01 4.85.07 1.17.05 1.8.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.27.07 1.65.07 4.85s-.01 3.58-.07 4.85c-.05 1.17-.25 1.8-.41 2.23-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.27.06-1.65.07-4.85.07s-3.58-.01-4.85-.07c-1.17-.05-1.8-.25-2.23-.41-.56-.22-.96-.48-1.38-.9-.42-.42-.68-.82-.9-1.38-.16-.42-.36-1.06-.41-2.23C2.17 15.58 2.16 15.2 2.16 12s.01-3.58.07-4.85c.05-1.17.25-1.8.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41C8.42 2.17 8.8 2.16 12 2.16zm0 5.68a4.16 4.16 0 100 8.32 4.16 4.16 0 000-8.32zm0 6.86a2.7 2.7 0 110-5.4 2.7 2.7 0 010 5.4zm5.3-7.02a.97.97 0 11-1.94 0 .97.97 0 011.94 0z',
  },
]
</script>

<template>
  <footer class="site-footer">
    <div class="container footer-inner">
      <div class="brand">
        <strong>🐾 Patitas Conectadas</strong>
        <p class="text-muted">
          Una herramienta sencilla para reunir mascotas con su familia y encontrar nuevos hogares.
        </p>
      </div>

      <!-- Las redes ocupan ahora la columna derecha, donde estaban los enlaces. -->
      <div class="social">
        <span class="social-label">Síguenos en Instagram</span>
        <ul>
          <li v-for="red in REDES" :key="red.nombre">
            <a
              :href="red.url"
              target="_blank"
              rel="noopener noreferrer"
              :aria-label="`${red.nombre}: ${red.usuario}`"
              :title="`${red.nombre} · ${red.usuario}`"
            >
              <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
                <path :d="red.icono" fill="currentColor" />
              </svg>
              <span class="social-user">{{ red.usuario }}</span>
            </a>
          </li>
        </ul>
      </div>

      <nav v-if="MOSTRAR_ENLACES" aria-label="Enlaces del pie">
        <router-link to="/buscar">Buscar mascotas</router-link>
        <router-link to="/publicar">Publicar</router-link>
        <router-link to="/noticias">Noticias y ayuda</router-link>
        <router-link to="/legal/privacidad">Política de privacidad</router-link>
        <router-link to="/legal/terminos">Términos y condiciones</router-link>
      </nav>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  border-top: 1px solid var(--border);
  background: var(--surface-2);
  padding: 28px 0;
  margin-top: 32px;
}

.footer-inner {
  display: grid;
  gap: 20px;
}

.footer-inner p { margin: 6px 0 0; max-width: 42ch; }

nav {
  display: grid;
  gap: 8px;
}

nav a {
  color: var(--text-soft);
  font-size: 0.95rem;
  transition: color var(--dur) var(--ease-out);
}
nav a:hover { color: var(--brand); }

/* --------------------------------------------------------------- redes */

.social { margin-top: 4px; }

.social-label {
  display: block;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.social ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.social a {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 8px 14px 8px 10px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--text-soft);
  font-size: 0.9rem;
  font-weight: 600;
  transition:
    color var(--dur) var(--ease-out),
    border-color var(--dur) var(--ease-out),
    background var(--dur) var(--ease-out),
    transform var(--dur-fast) var(--ease-out),
    box-shadow var(--dur) var(--ease-out);
}

.social a:hover {
  text-decoration: none;
  color: #fff;
  border-color: transparent;
  /* Degradado de Instagram; al agregar otra red conviene darle su propio color. */
  background: linear-gradient(45deg, #f09433, #dc2743 45%, #bc1888 80%);
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.social svg { flex: none; }

@media (min-width: 768px) {
  .footer-inner {
    grid-template-columns: 1fr auto;
    align-items: center;
  }
  nav {
    grid-template-columns: repeat(2, auto);
    column-gap: 32px;
  }
  /* El bloque se pega a la derecha pero se encoge al ancho de su contenido, de
     modo que el título queda alineado a la izquierda con el enlace de abajo en
     lugar de flotar suelto sobre él. */
  .social {
    width: fit-content;
    margin-left: auto;
  }
  .social-label { text-align: left; }
  .social ul { justify-content: flex-start; }
}
</style>
