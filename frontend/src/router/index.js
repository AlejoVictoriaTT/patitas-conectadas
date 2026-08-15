import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'

// Rutas privadas: no tiene sentido contarlas como visitas del público.
const SIN_METRICA = ['admin', 'gestionar', 'editar', 'mis-publicaciones', 'auth-callback']

const CLAVE_SESION = 'patitas.sesion-contada'

function esNuevaSesion() {
  try {
    if (sessionStorage.getItem(CLAVE_SESION)) return false
    sessionStorage.setItem(CLAVE_SESION, '1')
    return true
  } catch {
    // Modo privado o almacenamiento bloqueado: se cuenta la vista, no la sesión.
    return false
  }
}

const routes = [
  { path: '/', name: 'inicio', component: () => import('@/views/HomeView.vue') },
  { path: '/buscar', name: 'buscar', component: () => import('@/views/SearchView.vue') },
  {
    path: '/adopciones',
    name: 'adopciones',
    component: () => import('@/views/SearchView.vue'),
    props: { fixedType: 'adopcion' },
  },
  { path: '/publicar', name: 'publicar', component: () => import('@/views/PublishView.vue') },
  {
    path: '/mascotas/:type/:slug',
    name: 'mascota',
    component: () => import('@/views/PetDetailView.vue'),
    props: true,
  },
  {
    path: '/mis-publicaciones',
    name: 'mis-publicaciones',
    component: () => import('@/views/MyPostsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/gestionar/:token',
    name: 'gestionar',
    component: () => import('@/views/ManageView.vue'),
    props: true,
  },
  {
    path: '/publicacion/:id/editar',
    name: 'editar',
    component: () => import('@/views/EditPostView.vue'),
    props: true,
  },
  { path: '/ingresar', name: 'ingresar', component: () => import('@/views/LoginView.vue') },
  { path: '/crear-cuenta', name: 'crear-cuenta', component: () => import('@/views/RegisterView.vue') },
  { path: '/auth/callback', name: 'auth-callback', component: () => import('@/views/AuthCallbackView.vue') },
  { path: '/noticias', name: 'noticias', component: () => import('@/views/NewsView.vue') },
  { path: '/guias', name: 'guias', component: () => import('@/views/GuidesView.vue') },
  { path: '/emergencia', name: 'emergencia', component: () => import('@/views/EmergencyView.vue') },
  { path: '/guias/:slug', name: 'guia', component: () => import('@/views/ArticleView.vue'), props: true },
  // Las guías vivían en /noticias/:slug. Se redirige para no romper los enlaces
  // que ya se compartieron por WhatsApp ni lo que tenga indexado Google.
  { path: '/noticias/:slug', redirect: (to) => `/guias/${to.params.slug}` },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { requiresAdmin: true },
  },
  {
    path: '/legal/privacidad',
    name: 'privacidad',
    component: () => import('@/views/LegalView.vue'),
    props: { doc: 'privacidad' },
  },
  {
    path: '/legal/terminos',
    name: 'terminos',
    component: () => import('@/views/LegalView.vue'),
    props: { doc: 'terminos' },
  },
  { path: '/:pathMatch(.*)*', name: 'no-encontrado', component: () => import('@/views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash, behavior: 'smooth' }

    // Misma pantalla, solo cambian los parámetros de la URL: son los filtros de
    // búsqueda sincronizándose. Devolver `false` deja el scroll donde está; sin
    // esto, marcar una casilla te lanzaba de vuelta al inicio de la página y
    // había que bajar otra vez hasta los resultados.
    if (to.path === from.path) return false

    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.init()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'ingresar', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return auth.isAuthenticated ? { name: 'inicio' } : { name: 'ingresar', query: { redirect: to.fullPath } }
  }
  return true
})

// Se cuenta después de navegar, nunca antes: la métrica no puede retrasar ni
// bloquear la pantalla que el usuario pidió.
router.afterEach((to) => {
  if (SIN_METRICA.includes(to.name)) return
  api.trackVisit({ path: to.path, new_session: esNuevaSesion() })
})

export default router
