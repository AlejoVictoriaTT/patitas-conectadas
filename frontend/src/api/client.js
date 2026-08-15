/**
 * Cliente HTTP mínimo para la API.
 * Añade el token de sesión y traduce los errores a mensajes mostrables.
 */

const TOKEN_KEY = 'patitas.token'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* modo privado o almacenamiento bloqueado */
  }
}

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload || {}
    this.field = this.payload.campo || null
  }
}

async function request(path, { method = 'GET', body, headers = {}, manageToken, raw } = {}) {
  const finalHeaders = { ...headers }
  const token = getToken()
  if (token) finalHeaders.Authorization = `Bearer ${token}`
  if (manageToken) finalHeaders['X-Manage-Token'] = manageToken

  let payload = body
  if (body && !raw) {
    finalHeaders['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(path, { method, headers: finalHeaders, body: payload })
  } catch {
    throw new ApiError('No pudimos conectarnos. Revisa tu conexión a internet.', 0)
  }

  if (response.status === 204) return null

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const message =
      (data && data.detail) ||
      (response.status === 404
        ? 'No encontramos lo que buscas.'
        : 'Ocurrió un error inesperado. Inténtalo de nuevo.')
    throw new ApiError(typeof message === 'string' ? message : 'Revisa los datos enviados.', response.status, data)
  }

  return data
}

function query(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === false) return
    search.append(key, value)
  })
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export const api = {
  // ---- sistema
  config: () => request('/api/config'),
  authProviders: () => request('/api/auth/providers'),

  // ---- sesión
  register: (payload) => request('/api/auth/register', { method: 'POST', body: payload }),
  login: (payload) => request('/api/auth/login', { method: 'POST', body: payload }),
  me: () => request('/api/auth/me'),
  updateProfile: (payload) => request('/api/auth/me', { method: 'PATCH', body: payload }),
  changePassword: (payload) => request('/api/auth/password', { method: 'POST', body: payload }),
  claimPost: (manageToken) => request(`/api/auth/claim/${manageToken}`, { method: 'POST' }),

  // ---- publicaciones
  listPosts: (params) => request(`/api/posts${query(params)}`),
  postsCities: () => request('/api/posts/cities'),
  myPosts: () => request('/api/posts/mine'),
  createPost: (payload) => request('/api/posts', { method: 'POST', body: payload }),
  getPost: (identifier, manageToken) => request(`/api/posts/${identifier}`, { manageToken }),
  getByManageToken: (manageToken) => request(`/api/manage/${manageToken}`),
  updatePost: (id, payload, manageToken) =>
    request(`/api/posts/${id}`, { method: 'PATCH', body: payload, manageToken }),
  changeStatus: (id, status, manageToken) =>
    request(`/api/posts/${id}/status`, { method: 'POST', body: { status }, manageToken }),
  deletePost: (id, manageToken) => request(`/api/posts/${id}`, { method: 'DELETE', manageToken }),
  addPhotos: (id, photos, manageToken) =>
    request(`/api/posts/${id}/photos`, { method: 'POST', body: photos, manageToken }),
  deletePhoto: (id, photoId, manageToken) =>
    request(`/api/posts/${id}/photos/${photoId}`, { method: 'DELETE', manageToken }),
  setPrimaryPhoto: (id, photoId, manageToken) =>
    request(`/api/posts/${id}/photos/${photoId}/primary`, { method: 'POST', manageToken }),
  reorderPhotos: (id, photoIds, manageToken) =>
    request(`/api/posts/${id}/photos/reorder`, { method: 'POST', body: { photo_ids: photoIds }, manageToken }),

  // ---- fotos
  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/api/uploads', { method: 'POST', body: form, raw: true })
  },

  // ---- reportes
  reportReasons: () => request('/api/report-reasons'),
  reportPost: (identifier, payload) =>
    request(`/api/posts/${identifier}/report`, { method: 'POST', body: payload }),

  // ---- ubicaciones
  countries: () => request('/api/geo/countries'),
  regions: (country) => request(`/api/geo/regions${query({ country })}`),
  cities: (country, region) => request(`/api/geo/cities${query({ country, region })}`),
  searchCities: (q, country) => request(`/api/geo/search${query({ q, country, limit: 25 })}`),

  // ---- métricas
  // Se envía en segundo plano; si falla no pasa nada y nadie se entera.
  trackVisit: (payload) =>
    request('/api/visits', { method: 'POST', body: payload }).catch(() => null),

  // ---- noticias propias (guías y recursos)
  articles: (params) => request(`/api/articles${query(params)}`),
  article: (slug) => request(`/api/articles/${slug}`),
  articleCategories: () => request('/api/articles/categories'),

  // ---- actualidad (notas de medios traídas por RSS)
  news: (params) => request(`/api/news${query(params)}`),
  newsTones: () => request('/api/news/tones'),
  newsRegions: () => request('/api/news/regions'),

  // ---- administración
  admin: {
    stats: () => request('/api/admin/stats'),
    posts: (params) => request(`/api/admin/posts${query(params)}`),
    setVisibility: (id, payload) => request(`/api/admin/posts/${id}/visibility`, { method: 'POST', body: payload }),
    deletePost: (id) => request(`/api/admin/posts/${id}`, { method: 'DELETE' }),
    reports: (params) => request(`/api/admin/reports${query(params)}`),
    updateReport: (id, payload) => request(`/api/admin/reports/${id}`, { method: 'PATCH', body: payload }),
    users: (params) => request(`/api/admin/users${query(params)}`),
    updateUser: (id, payload) => request(`/api/admin/users/${id}`, { method: 'PATCH', body: payload }),
    news: (params) => request(`/api/admin/news${query(params)}`),
    syncNews: () => request('/api/admin/news/sync', { method: 'POST' }),
    setNewsVisibility: (id, payload) =>
      request(`/api/admin/news/${id}/visibility`, { method: 'POST', body: payload }),
    articles: () => request('/api/admin/articles'),
    createArticle: (payload) => request('/api/admin/articles', { method: 'POST', body: payload }),
    updateArticle: (id, payload) => request(`/api/admin/articles/${id}`, { method: 'PUT', body: payload }),
    deleteArticle: (id) => request(`/api/admin/articles/${id}`, { method: 'DELETE' }),
  },
}
