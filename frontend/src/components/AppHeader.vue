<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)

watch(() => route.fullPath, () => { menuOpen.value = false })

function logout() {
  auth.logout()
  menuOpen.value = false
  router.push({ name: 'inicio' })
}
</script>

<template>
  <header class="site-header">
    <div class="container header-inner">
      <router-link to="/" class="brand" aria-label="Patitas Conectadas, ir al inicio">
        <span class="brand-mark" aria-hidden="true">🐾</span>
        <span class="brand-text">Patitas<span>Conectadas</span></span>
      </router-link>

      <nav class="desktop-nav" aria-label="Navegación principal">
        <router-link to="/buscar">Buscar mascotas</router-link>
        <router-link to="/adopciones">Adopciones</router-link>
        <router-link to="/noticias">Noticias</router-link>
        <router-link to="/guias">Guías</router-link>
        <router-link to="/emergencia">Emergencia</router-link>
        <router-link v-if="auth.isAuthenticated" to="/mis-publicaciones">Mis publicaciones</router-link>
        <router-link v-if="auth.isAdmin" to="/admin">Panel</router-link>
      </nav>

      <div class="header-actions">
        <router-link class="btn btn-primary btn-sm publish-cta" to="/publicar">
          <span aria-hidden="true">🐾</span> Publicar
        </router-link>

        <template v-if="auth.isAuthenticated">
          <div class="account">
            <button
              class="account-btn"
              type="button"
              :aria-expanded="menuOpen"
              aria-haspopup="true"
              @click="menuOpen = !menuOpen"
            >
              <span class="avatar" aria-hidden="true">{{ auth.displayName.charAt(0) || '🐾' }}</span>
              <span class="hide-mobile">{{ auth.displayName }}</span>
            </button>
            <div v-if="menuOpen" class="account-menu">
              <router-link to="/mis-publicaciones">Mis publicaciones</router-link>
              <router-link v-if="auth.isAdmin" to="/admin">Panel administrativo</router-link>
              <button type="button" @click="logout">Cerrar sesión</button>
            </div>
          </div>
        </template>
        <router-link v-else class="btn btn-quiet btn-sm login-link" to="/ingresar">Iniciar sesión</router-link>
      </div>
    </div>
  </header>
</template>

<style scoped>
.site-header {
  position: sticky;
  top: 0;
  z-index: 40;
  background: rgba(255, 251, 247, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
}

.header-inner {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: var(--header-h);
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text);
  font-weight: 800;
  text-decoration: none;
  flex: none;
}
.brand:hover { text-decoration: none; }

.brand-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--brand);
  font-size: 1.05rem;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1;
  font-size: 0.95rem;
}
.brand-text span {
  font-weight: 500;
  color: var(--brand);
  font-size: 0.8rem;
}

.desktop-nav { display: none; }

.header-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
}

.publish-cta { display: none; }
.login-link { white-space: nowrap; }

.account { position: relative; }

.account-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 4px 10px 4px 4px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border);
  background: var(--surface);
  cursor: pointer;
  font-weight: 600;
}

.avatar {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--brand-light);
  color: var(--brand-dark);
  font-weight: 800;
  text-transform: uppercase;
}

.account-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 210px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  display: grid;
  padding: 6px;
  z-index: 50;
}

.account-menu a,
.account-menu button {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  text-align: left;
  background: none;
  border: none;
  color: var(--text);
  cursor: pointer;
  font-size: 0.95rem;
}
.account-menu a:hover,
.account-menu button:hover {
  background: var(--surface-2);
  text-decoration: none;
}

@media (min-width: 768px) {
  /*
    Con seis enlaces (más los de sesión) la barra no cabe entre 768 y 1024px.
    En vez de esconder secciones, el menú se desplaza en horizontal: todo sigue
    siendo alcanzable y en pantallas grandes ni se nota que puede hacerlo.
    `min-width: 0` es lo que permite que el flex encoja en vez de empujar.
  */
  .desktop-nav {
    display: flex;
    gap: 2px;
    margin-left: 12px;
    min-width: 0;
    overflow-x: auto;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }
  .desktop-nav::-webkit-scrollbar { display: none; }

  .desktop-nav a {
    padding: 8px 10px;
    border-radius: var(--radius-pill);
    color: var(--text-soft);
    font-weight: 600;
    font-size: 0.92rem;
    white-space: nowrap;
  }
  .desktop-nav a:hover {
    background: var(--surface-2);
    color: var(--text);
    text-decoration: none;
  }
  .desktop-nav a.router-link-active {
    color: var(--brand);
    background: var(--brand-light);
  }
  .publish-cta { display: inline-flex; }
  .brand-text { font-size: 1.05rem; }
}

@media (min-width: 1100px) {
  /* Ya hay espacio de sobra: se recupera el respiro entre enlaces. */
  .desktop-nav { gap: 4px; margin-left: 16px; }
  .desktop-nav a { padding: 8px 12px; font-size: 0.95rem; }
}
</style>
