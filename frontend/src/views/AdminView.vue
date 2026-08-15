<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { categoryLabel, formatShortDate, postTitle } from '@/lib/format'
import { setPageTitle } from '@/lib/head'

const auth = useAuthStore()
const ui = useUiStore()

const TABS = [
  { key: 'resumen', label: '📊 Resumen' },
  { key: 'publicaciones', label: '🐾 Publicaciones' },
  { key: 'reportes', label: '⚠️ Reportes' },
  { key: 'usuarios', label: '👤 Usuarios' },
  { key: 'contenido', label: '📰 Contenido' },
]

const tab = ref('resumen')
const loading = ref(false)

const stats = ref(null)
const posts = reactive({ items: [], total: 0, page: 1, pages: 1 })
const postFilters = reactive({ q: '', city: '', type: '', only_hidden: false, only_reported: false })
const reports = ref([])
const reportStatus = ref('pendiente')
const users = ref([])
const userQuery = ref('')
const articles = ref([])

const editingArticle = ref(null)
const articleForm = reactive({
  title: '',
  category: 'noticia',
  excerpt: '',
  content: '',
  image_url: '',
  city: '',
  contact_url: '',
  is_published: true,
})

const CATEGORIAS = [
  'noticia', 'albergue', 'hogar_de_paso', 'fundacion', 'jornada_adopcion',
  'esterilizacion', 'vacunacion', 'consejo', 'bienestar_animal',
]

// ------------------------------------------------- ingesta de noticias

const syncing = ref(false)
const syncResult = ref(null)

async function syncNews() {
  syncing.value = true
  try {
    syncResult.value = await api.admin.syncNews()
    ui.success(`Listo: ${syncResult.value.nuevas} noticias nuevas.`)
  } catch (error) {
    ui.error(error.message)
  } finally {
    syncing.value = false
  }
}

// ------------------------------------------------------------------ visitas

const formatNumber = (valor) => new Intl.NumberFormat('es-CO').format(valor || 0)

const DIAS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb']

function diaCorto(iso) {
  const fecha = new Date(`${iso}T12:00:00`)
  return `${DIAS[fecha.getDay()]} ${fecha.getDate()}`
}

// La barra más alta del periodo marca el 100%; con 0 visitas no se divide.
const maxVisitasDia = computed(() =>
  Math.max(1, ...(stats.value?.visits?.daily || []).map((d) => d.views)),
)

function porcentaje(valor, maximo) {
  if (!valor) return 0
  return Math.max(4, Math.round((valor / maximo) * 100)) // mínimo visible
}

const MOTIVOS = {
  informacion_falsa: 'Información falsa',
  contenido_inapropiado: 'Contenido inapropiado',
  duplicada: 'Duplicada',
  venta_de_animales: 'Venta de animales',
  spam: 'Spam',
  maltrato: 'Posible maltrato',
  otro: 'Otro',
}

async function run(fn) {
  loading.value = true
  try {
    await fn()
  } catch (error) {
    ui.error(error.message)
  } finally {
    loading.value = false
  }
}

const loadStats = () => run(async () => { stats.value = await api.admin.stats() })

const loadPosts = (page = 1) =>
  run(async () => {
    const data = await api.admin.posts({ ...postFilters, page, page_size: 20 })
    Object.assign(posts, data)
  })

const loadReports = () =>
  run(async () => { reports.value = await api.admin.reports({ status: reportStatus.value }) })

const loadUsers = () => run(async () => { users.value = await api.admin.users({ q: userQuery.value }) })

const loadArticles = () => run(async () => { articles.value = await api.admin.articles() })

async function toggleVisibility(post) {
  await run(async () => {
    await api.admin.setVisibility(post.id, {
      is_active: !post.is_active,
      hidden_reason: post.is_active ? 'Desactivada por moderación.' : null,
    })
    ui.success(post.is_active ? 'Publicación desactivada.' : 'Publicación reactivada.')
    await loadPosts(posts.page)
  })
}

async function resolveReport(report, status, hidePost = false) {
  await run(async () => {
    await api.admin.updateReport(report.id, { status, hide_post: hidePost })
    ui.success('Reporte actualizado.')
    await loadReports()
  })
}

async function toggleUser(user, field) {
  await run(async () => {
    await api.admin.updateUser(user.id, { [field]: !user[field] })
    ui.success('Usuario actualizado.')
    await loadUsers()
  })
}

function editArticle(article) {
  editingArticle.value = article?.id || 'nuevo'
  Object.assign(articleForm, {
    title: article?.title || '',
    category: article?.category || 'noticia',
    excerpt: article?.excerpt || '',
    content: article?.content || '',
    image_url: article?.image_url || '',
    city: article?.city || '',
    contact_url: article?.contact_url || '',
    is_published: article ? article.is_published : true,
  })
}

async function saveArticle() {
  await run(async () => {
    const payload = {
      ...articleForm,
      excerpt: articleForm.excerpt || null,
      image_url: articleForm.image_url || null,
      city: articleForm.city || null,
      contact_url: articleForm.contact_url || null,
    }
    if (editingArticle.value === 'nuevo') await api.admin.createArticle(payload)
    else await api.admin.updateArticle(editingArticle.value, payload)
    ui.success('Contenido guardado.')
    editingArticle.value = null
    await loadArticles()
  })
}

async function deleteArticle(article) {
  if (!window.confirm(`¿Eliminar «${article.title}»?`)) return
  await run(async () => {
    await api.admin.deleteArticle(article.id)
    ui.success('Contenido eliminado.')
    await loadArticles()
  })
}

watch(tab, (value) => {
  if (value === 'resumen' && !stats.value) loadStats()
  if (value === 'publicaciones' && !posts.items.length) loadPosts()
  if (value === 'reportes') loadReports()
  if (value === 'usuarios' && !users.value.length) loadUsers()
  if (value === 'contenido' && !articles.value.length) loadArticles()
})

watch(reportStatus, loadReports)

onMounted(() => {
  setPageTitle('Panel administrativo')
  loadStats()
})
</script>

<template>
  <div class="container section admin">
    <header class="head">
      <div>
        <h1>Panel administrativo</h1>
        <p class="text-soft">Sesión de {{ auth.user?.name }}</p>
      </div>
    </header>

    <div class="chip-group tabs">
      <button
        v-for="item in TABS"
        :key="item.key"
        type="button"
        class="chip"
        :class="{ 'is-selected': tab === item.key }"
        @click="tab = item.key"
      >
        {{ item.label }}
      </button>
    </div>

    <!-- ================================= RESUMEN ================================= -->
    <section v-if="tab === 'resumen'">
      <!-- Visibilidad: ¿nos está viendo alguien? -->
      <div v-if="stats?.visits" class="visits-block">
        <h2 class="block-title">👁️ Visibilidad del sitio</h2>

        <p v-if="stats.visits.unavailable" class="alert alert-warm">
          El contador de visitas aún no está activo en esta base de datos. Se activa solo
          en el próximo arranque del servidor con <code>AUTO_CREATE_TABLES=1</code>.
        </p>
        <div class="stat-grid">
          <div class="panel stat is-highlight">
            <span>Visitas totales</span>
            <strong>{{ formatNumber(stats.visits.total) }}</strong>
            <small class="text-muted">Desde que se activó el contador</small>
          </div>
          <div class="panel stat">
            <span>Hoy</span>
            <strong>{{ formatNumber(stats.visits.today) }}</strong>
          </div>
          <div class="panel stat">
            <span>Últimos 7 días</span>
            <strong>{{ formatNumber(stats.visits.last_7_days) }}</strong>
          </div>
          <div class="panel stat">
            <span>Últimos 30 días</span>
            <strong>{{ formatNumber(stats.visits.last_30_days) }}</strong>
          </div>
          <div class="panel stat">
            <span>Visitantes (sesiones)</span>
            <strong>{{ formatNumber(stats.visits.sessions_total) }}</strong>
            <small class="text-muted">7 días: {{ formatNumber(stats.visits.sessions_last_7_days) }}</small>
          </div>
          <div class="panel stat">
            <span>Aperturas de publicaciones</span>
            <strong>{{ formatNumber(stats.total_post_views) }}</strong>
          </div>
        </div>

        <!-- Barras de los últimos 7 días -->
        <div v-if="stats.visits.daily?.length" class="panel chart">
          <h3>Visitas por día</h3>
          <ul class="bars">
            <li v-for="dia in stats.visits.daily" :key="dia.day">
              <span class="bar-label">{{ diaCorto(dia.day) }}</span>
              <span class="bar-track">
                <span
                  class="bar-fill"
                  :style="{ width: `${porcentaje(dia.views, maxVisitasDia)}%` }"
                ></span>
              </span>
              <strong class="bar-value">{{ formatNumber(dia.views) }}</strong>
            </li>
          </ul>
        </div>

        <div v-if="stats.most_viewed?.length" class="panel cities">
          <h2>Publicaciones más vistas</h2>
          <ul>
            <li v-for="row in stats.most_viewed" :key="row.id">
              <router-link :to="row.url">{{ row.title }}</router-link>
              <strong>👁️ {{ formatNumber(row.views) }}</strong>
            </li>
          </ul>
        </div>
      </div>

      <h2 class="block-title">📊 Publicaciones</h2>
      <div v-if="stats" class="stat-grid">
        <div class="panel stat"><span>Publicaciones</span><strong>{{ stats.total_posts }}</strong></div>
        <div class="panel stat"><span>Activas</span><strong>{{ stats.active_posts }}</strong></div>
        <div class="panel stat"><span>🔴 Perdidas</span><strong>{{ stats.lost }}</strong></div>
        <div class="panel stat"><span>🟢 Encontradas</span><strong>{{ stats.found }}</strong></div>
        <div class="panel stat"><span>💙 En adopción</span><strong>{{ stats.adoption }}</strong></div>
        <div class="panel stat"><span>Casos resueltos</span><strong>{{ stats.resolved }}</strong></div>
        <div class="panel stat"><span>Reportes pendientes</span><strong>{{ stats.pending_reports }}</strong></div>
        <div class="panel stat"><span>Usuarios</span><strong>{{ stats.users }}</strong></div>
        <div class="panel stat"><span>Últimos 7 días</span><strong>{{ stats.posts_last_7_days }}</strong></div>
      </div>

      <div v-if="stats?.top_cities?.length" class="panel cities">
        <h2>Ciudades con más publicaciones</h2>
        <ul>
          <li v-for="row in stats.top_cities" :key="row.city">
            <span>📍 {{ row.city }}</span>
            <strong>{{ row.total }}</strong>
          </li>
        </ul>
      </div>
    </section>

    <!-- ============================== PUBLICACIONES ============================== -->
    <section v-else-if="tab === 'publicaciones'">
      <div class="panel filters">
        <div class="form-grid cols-2">
          <div class="field">
            <label class="label" for="a-q">Buscar</label>
            <input id="a-q" v-model="postFilters.q" class="input" type="search" placeholder="Nombre, correo o código" />
          </div>
          <div class="field">
            <label class="label" for="a-city">Ciudad</label>
            <input id="a-city" v-model="postFilters.city" class="input" type="text" />
          </div>
          <div class="field">
            <label class="label" for="a-type">Tipo</label>
            <select id="a-type" v-model="postFilters.type" class="select">
              <option value="">Todos</option>
              <option value="perdida">Perdidas</option>
              <option value="encontrada">Encontradas</option>
              <option value="adopcion">En adopción</option>
            </select>
          </div>
          <div class="field">
            <label class="switch-row"><span>Solo ocultas</span><input v-model="postFilters.only_hidden" type="checkbox" /></label>
            <label class="switch-row"><span>Solo reportadas</span><input v-model="postFilters.only_reported" type="checkbox" /></label>
          </div>
        </div>
        <button class="btn btn-primary btn-block" type="button" @click="loadPosts(1)">Aplicar filtros</button>
      </div>

      <p class="text-soft">{{ posts.total }} publicaciones</p>

      <div class="table-wrap">
        <table class="data">
          <thead>
            <tr>
              <th>Mascota</th>
              <th>Tipo / estado</th>
              <th>Ciudad</th>
              <th>Fecha</th>
              <th>Visitas</th>
              <th>Reportes</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="post in posts.items" :key="post.id">
              <td>
                <router-link :to="post.url">{{ postTitle(post) }}</router-link>
                <br />
                <small class="text-muted">{{ post.public_id }}</small>
              </td>
              <td>
                <StatusBadge :post="post" variant="type" />
                <br />
                <StatusBadge :post="post" />
              </td>
              <td>{{ post.city }}</td>
              <td>{{ formatShortDate(post.created_at) }}</td>
              <td class="nowrap">👁️ {{ formatNumber(post.views || 0) }}</td>
              <td>{{ post.reports_count || 0 }}</td>
              <td>
                <button class="btn btn-ghost btn-sm" type="button" @click="toggleVisibility(post)">
                  {{ post.is_active ? 'Desactivar' : 'Reactivar' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="posts.pages > 1" class="pager">
        <button class="btn btn-ghost btn-sm" type="button" :disabled="posts.page <= 1" @click="loadPosts(posts.page - 1)">
          ← Anterior
        </button>
        <span class="text-soft">Página {{ posts.page }} de {{ posts.pages }}</span>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="posts.page >= posts.pages" @click="loadPosts(posts.page + 1)">
          Siguiente →
        </button>
      </div>
    </section>

    <!-- ================================ REPORTES ================================= -->
    <section v-else-if="tab === 'reportes'">
      <div class="chip-group tabs">
        <button
          v-for="estado in ['pendiente', 'revisado', 'descartado']"
          :key="estado"
          type="button"
          class="chip"
          :class="{ 'is-selected': reportStatus === estado }"
          @click="reportStatus = estado"
        >
          {{ estado }}
        </button>
      </div>

      <p v-if="!reports.length" class="text-soft">No hay reportes con este estado.</p>

      <ul v-else class="report-list">
        <li v-for="report in reports" :key="report.id" class="panel">
          <div class="report-head">
            <strong>{{ MOTIVOS[report.reason] || report.reason }}</strong>
            <span class="text-muted small">{{ formatShortDate(report.created_at) }}</span>
          </div>
          <p v-if="report.details" class="text-soft">{{ report.details }}</p>
          <p v-if="report.post" class="text-muted small">
            Publicación:
            <router-link :to="`/mascotas/${report.post.type}/${report.post.slug}`">
              {{ report.post.pet_name || 'Sin nombre' }} — {{ report.post.city }}
            </router-link>
            · {{ report.post.reports_count }} reportes ·
            {{ report.post.is_active ? 'visible' : 'oculta' }}
          </p>
          <div class="row" v-if="report.status === 'pendiente'">
            <button class="btn btn-danger btn-sm" type="button" @click="resolveReport(report, 'revisado', true)">
              Ocultar publicación
            </button>
            <button class="btn btn-ghost btn-sm" type="button" @click="resolveReport(report, 'revisado')">
              Marcar revisado
            </button>
            <button class="btn btn-quiet btn-sm" type="button" @click="resolveReport(report, 'descartado')">
              Descartar
            </button>
          </div>
        </li>
      </ul>
    </section>

    <!-- ================================ USUARIOS ================================= -->
    <section v-else-if="tab === 'usuarios'">
      <div class="panel filters">
        <div class="field">
          <label class="label" for="u-q">Buscar usuario</label>
          <input id="u-q" v-model="userQuery" class="input" type="search" placeholder="Nombre o correo" />
        </div>
        <button class="btn btn-primary btn-block" type="button" @click="loadUsers">Buscar</button>
      </div>

      <div class="table-wrap">
        <table class="data">
          <thead>
            <tr><th>Nombre</th><th>Correo</th><th>Registro</th><th>Estado</th><th>Acciones</th></tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.name }}</td>
              <td>{{ user.email }}</td>
              <td>{{ formatShortDate(user.created_at) }}</td>
              <td>
                <span class="badge" :class="user.is_admin ? 'badge-adopcion' : 'badge-neutral'">
                  {{ user.is_admin ? 'Administrador' : 'Usuario' }}
                </span>
              </td>
              <td class="nowrap">
                <button class="btn btn-quiet btn-sm" type="button" @click="toggleUser(user, 'is_admin')">
                  {{ user.is_admin ? 'Quitar admin' : 'Hacer admin' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ================================ CONTENIDO ================================ -->
    <section v-else>
      <div class="row content-head">
        <h2>Noticias y recursos</h2>
        <button class="btn btn-primary btn-sm" type="button" @click="editArticle(null)">+ Nuevo contenido</button>
      </div>

      <!-- Actualidad: ingesta de noticias externas -->
      <div class="panel news-sync">
        <h3>Noticias de medios</h3>
        <p class="text-soft small">
          Se traen solas una vez al día. Este botón fuerza la sincronización ahora mismo, útil
          después de un cambio o si quieres ver el resultado sin esperar.
        </p>
        <div class="row">
          <button class="btn btn-primary btn-sm" type="button" :disabled="syncing" @click="syncNews">
            {{ syncing ? 'Sincronizando…' : 'Sincronizar ahora' }}
          </button>
          <span v-if="syncResult" class="text-soft small">
            {{ syncResult.nuevas }} nuevas · {{ syncResult.revisadas }} revisadas ·
            {{ syncResult.purgadas }} retiradas por antigüedad ·
            {{ syncResult.fuentes_ok }} fuentes leídas
            <template v-if="syncResult.fuentes_fallidas?.length">
              · fallaron: {{ syncResult.fuentes_fallidas.join(', ') }}
            </template>
          </span>
        </div>
      </div>

      <form v-if="editingArticle" class="panel" @submit.prevent="saveArticle">
        <h3>{{ editingArticle === 'nuevo' ? 'Nuevo contenido' : 'Editar contenido' }}</h3>
        <div class="form-grid cols-2">
          <div class="field field-full">
            <label class="label" for="ar-title">Título</label>
            <input id="ar-title" v-model="articleForm.title" class="input" type="text" required />
          </div>
          <div class="field">
            <label class="label" for="ar-cat">Categoría</label>
            <select id="ar-cat" v-model="articleForm.category" class="select">
              <option v-for="c in CATEGORIAS" :key="c" :value="c">{{ categoryLabel(c) }}</option>
            </select>
          </div>
          <div class="field">
            <label class="label" for="ar-city">Ciudad <span class="optional">(opcional)</span></label>
            <input id="ar-city" v-model="articleForm.city" class="input" type="text" />
          </div>
          <div class="field field-full">
            <label class="label" for="ar-excerpt">Resumen <span class="optional">(opcional)</span></label>
            <input id="ar-excerpt" v-model="articleForm.excerpt" class="input" type="text" maxlength="400" />
          </div>
          <div class="field field-full">
            <label class="label" for="ar-content">Contenido</label>
            <textarea id="ar-content" v-model="articleForm.content" class="textarea" rows="8" required></textarea>
          </div>
          <div class="field">
            <label class="label" for="ar-image">URL de imagen <span class="optional">(opcional)</span></label>
            <input id="ar-image" v-model="articleForm.image_url" class="input" type="url" />
          </div>
          <div class="field">
            <label class="label" for="ar-link">Enlace de contacto <span class="optional">(opcional)</span></label>
            <input id="ar-link" v-model="articleForm.contact_url" class="input" type="url" />
          </div>
          <div class="field field-full">
            <label class="switch-row">
              <span>Publicado</span>
              <input v-model="articleForm.is_published" type="checkbox" />
            </label>
          </div>
        </div>
        <div class="row">
          <button class="btn btn-primary" type="submit" :disabled="loading">Guardar</button>
          <button class="btn btn-ghost" type="button" @click="editingArticle = null">Cancelar</button>
        </div>
      </form>

      <div class="table-wrap">
        <table class="data">
          <thead>
            <tr><th>Título</th><th>Categoría</th><th>Ciudad</th><th>Estado</th><th>Acciones</th></tr>
          </thead>
          <tbody>
            <tr v-for="article in articles" :key="article.id">
              <td>{{ article.title }}</td>
              <td>{{ categoryLabel(article) }}</td>
              <td>{{ article.city || 'Nacional' }}</td>
              <td>
                <span class="badge" :class="article.is_published ? 'badge-encontrada' : 'badge-cerrada'">
                  {{ article.is_published ? 'Publicado' : 'Borrador' }}
                </span>
              </td>
              <td class="nowrap">
                <button class="btn btn-quiet btn-sm" type="button" @click="editArticle(article)">Editar</button>
                <button class="btn btn-quiet btn-sm" type="button" @click="deleteArticle(article)">Eliminar</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.head { margin-bottom: 14px; }
.head h1 { margin-bottom: 2px; }
.head p { margin: 0; }

.tabs { margin-bottom: 18px; }

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 18px;
}

.stat { display: grid; gap: 2px; padding: 14px; }
.stat span { color: var(--text-soft); font-size: 0.85rem; }
.stat strong { font-size: 1.6rem; }
.stat small { font-size: 0.78rem; }

/* --------------------------------------------------------------- visitas */

.news-sync { margin-bottom: 16px; }
.news-sync h3 { margin-top: 0; font-size: 1.02rem; }
.news-sync p { margin: 0 0 10px; max-width: 62ch; }

.block-title {
  font-size: 1.05rem;
  margin: 22px 0 10px;
}
.block-title:first-child { margin-top: 0; }

.visits-block { margin-bottom: 8px; }

.stat.is-highlight {
  border-color: var(--brand);
  background: linear-gradient(160deg, var(--brand-light), var(--surface) 70%);
}
.stat.is-highlight strong { color: var(--brand-dark); }

.chart { margin-top: 14px; }
.chart h3 { margin-top: 0; font-size: 1rem; }

.bars { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }

.bars li {
  display: grid;
  grid-template-columns: 62px 1fr auto;
  align-items: center;
  gap: 10px;
  font-size: 0.88rem;
}

.bar-label { color: var(--text-soft); }

.bar-track {
  height: 10px;
  border-radius: var(--radius-pill);
  background: var(--surface-2);
  overflow: hidden;
}

.bar-fill {
  display: block;
  height: 100%;
  border-radius: var(--radius-pill);
  background: linear-gradient(90deg, var(--brand), var(--accent));
  /* Crece con la misma curva que el resto de la interfaz. */
  transition: width var(--dur-slow) var(--ease-out);
}

.bar-value { font-variant-numeric: tabular-nums; }

.cities li a { color: var(--text); }

.cities ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.cities li { display: flex; justify-content: space-between; border-bottom: 1px dashed var(--border); padding-bottom: 6px; }
.cities h2 { margin-top: 0; font-size: 1.05rem; }

.filters { margin-bottom: 14px; }

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 14px;
}

.report-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
.report-head { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 6px; }

.content-head { justify-content: space-between; margin-bottom: 12px; }
.content-head h2 { margin: 0; font-size: 1.15rem; }

@media (min-width: 768px) {
  .stat-grid { grid-template-columns: repeat(3, 1fr); }
}

@media (min-width: 1024px) {
  .stat-grid { grid-template-columns: repeat(5, 1fr); }
}
</style>
