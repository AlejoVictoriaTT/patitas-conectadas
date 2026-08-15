<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import CitySelect from '@/components/CitySelect.vue'
import PhotoUploader from '@/components/PhotoUploader.vue'
import ShareButtons from '@/components/ShareButtons.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { formatDate, postTitle, speciesEmoji, todayISO, typeMeta } from '@/lib/format'

const route = useRoute()
const auth = useAuthStore()
const ui = useUiStore()

const DRAFT_KEY = 'patitas.borrador'
const PASOS = ['Tipo', 'Fotos', 'Mascota', 'Lugar y fecha', 'Contacto', 'Revisar']

const ESPECIES = [
  { value: 'perro', label: 'Perro' },
  { value: 'gato', label: 'Gato' },
  { value: 'otro', label: 'Otro' },
]

const step = ref(0)
const sending = ref(false)
const error = ref('')
const showOptional = ref(false)
const result = ref(null)

const form = reactive({
  type: '',
  photos: [],
  species: '',
  pet_name: '',
  breed: '',
  sex: '',
  age: '',
  color: '',
  size: '',
  has_collar: null,
  has_tag: null,
  special_marks: '',
  description: '',
  city: null,
  neighborhood: '',
  address: '',
  event_date: todayISO(),
  contact_name: '',
  contact_whatsapp: '',
  contact_phone: '',
  contact_email: '',
  contact_note: '',
  guest_email: '',
  website: '', // honeypot antispam
})

const meta = computed(() => (form.type ? typeMeta(form.type) : null))
const progress = computed(() => ((step.value + 1) / PASOS.length) * 100)

const previewPost = computed(() => {
  const primary = form.photos.find((p) => p.is_primary) || form.photos[0]
  return {
    type: form.type || 'perdida',
    type_label: meta.value?.label || '',
    status_label: form.type === 'perdida'
      ? 'Perdida'
      : form.type === 'encontrada'
        ? 'Encontrada — buscando a su familia'
        : 'Disponible para adopción',
    status: form.type === 'perdida' ? 'perdida' : form.type === 'encontrada' ? 'buscando_familia' : 'disponible',
    species: form.species,
    pet_name: form.pet_name,
    photo_url: primary?.url || null,
  }
})

// -------------------------------------------------------------- borrador local

function saveDraft() {
  try {
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ ...form, website: '' }))
  } catch {
    /* sin almacenamiento */
  }
}

function clearDraft() {
  try {
    sessionStorage.removeItem(DRAFT_KEY)
  } catch {
    /* sin almacenamiento */
  }
}

watch(form, saveDraft, { deep: true })

onMounted(() => {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY)
    if (raw) Object.assign(form, JSON.parse(raw))
  } catch {
    /* sin almacenamiento */
  }

  const tipo = route.query.tipo
  if (['perdida', 'encontrada', 'adopcion'].includes(tipo)) {
    form.type = tipo
    if (step.value === 0) step.value = 1
  }

  if (auth.user) {
    form.contact_name = form.contact_name || auth.user.name
    form.contact_email = form.contact_email || auth.user.email
    if (auth.user.phone) form.contact_whatsapp = form.contact_whatsapp || auth.user.phone
  }
  if (ui.city && !form.city) form.city = ui.city
})

// ------------------------------------------------------------------ validación

function validateStep(index) {
  switch (index) {
    case 0:
      if (!form.type) return 'Elige qué quieres publicar.'
      return ''
    case 1:
      if (!form.photos.length) return 'Agrega al menos una foto para ayudar a identificar a la mascota.'
      return ''
    case 2:
      if (!form.species) return 'Selecciona la especie de la mascota.'
      if (form.description.trim().length < 10) return 'Cuéntanos algo sobre la mascota (mínimo 10 caracteres).'
      return ''
    case 3:
      if (!form.city) return 'Selecciona la ciudad.'
      if (!form.event_date) return 'Indica la fecha.'
      if (form.event_date > todayISO()) return 'La fecha no puede ser posterior a hoy.'
      return ''
    case 4:
      if (!form.contact_whatsapp && !form.contact_phone && !form.contact_email) {
        return 'Agrega al menos un medio de contacto: WhatsApp, teléfono o correo.'
      }
      return ''
    default:
      return ''
  }
}

function next() {
  const message = validateStep(step.value)
  if (message) {
    error.value = message
    return
  }
  error.value = ''
  step.value = Math.min(step.value + 1, PASOS.length - 1)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function back() {
  error.value = ''
  step.value = Math.max(step.value - 1, 0)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function goTo(index) {
  if (index > step.value) return
  error.value = ''
  step.value = index
}

// -------------------------------------------------------------------- publicar

async function submit() {
  for (let i = 0; i < PASOS.length - 1; i += 1) {
    const message = validateStep(i)
    if (message) {
      error.value = message
      step.value = i
      return
    }
  }

  sending.value = true
  error.value = ''
  try {
    const payload = {
      type: form.type,
      species: form.species,
      description: form.description.trim(),
      event_date: form.event_date,
      location: {
        country: form.city.country || 'Colombia',
        region: form.city.region || null,
        city: form.city.city,
        neighborhood: form.neighborhood.trim() || null,
        address: form.address.trim() || null,
      },
      contact: {
        name: form.contact_name.trim() || null,
        whatsapp: form.contact_whatsapp.trim() || null,
        phone: form.contact_phone.trim() || null,
        email: form.contact_email.trim() || null,
        note: form.contact_note.trim() || null,
      },
      photos: form.photos.map((p) => ({ url: p.url, is_primary: Boolean(p.is_primary) })),
      pet_name: form.pet_name.trim() || null,
      breed: form.breed.trim() || null,
      sex: form.sex || null,
      age: form.age.trim() || null,
      color: form.color.trim() || null,
      size: form.size || null,
      has_collar: form.has_collar,
      has_tag: form.has_tag,
      special_marks: form.special_marks.trim() || null,
      guest_email: form.guest_email.trim() || form.contact_email.trim() || null,
      website: form.website,
    }

    const data = await api.createPost(payload)
    result.value = data

    if (data.manage_token) {
      ui.rememberGuestPost({
        token: data.manage_token,
        url: data.post.url,
        name: postTitle(data.post),
        type: data.post.type,
        created_at: new Date().toISOString(),
      })
    }
    clearDraft()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (err) {
    error.value = err.message
  } finally {
    sending.value = false
  }
}

function publishAnother() {
  result.value = null
  Object.assign(form, {
    photos: [],
    pet_name: '',
    breed: '',
    color: '',
    special_marks: '',
    description: '',
  })
  step.value = 0
}
</script>

<template>
  <div v-if="result" class="container section confirm">
    <div class="panel success-panel text-center">
      <div class="success-emoji" aria-hidden="true">🐾</div>
      <h1>¡Tu publicación está activa!</h1>
      <p class="text-soft">
        Gracias por ayudarnos a encontrar una familia, un hogar o un nuevo comienzo para esta mascota.
      </p>

      <div class="preview-mini">
        <img v-if="result.post.photo_url" :src="result.post.photo_url" alt="Foto principal de la publicación" />
        <div>
          <strong>{{ postTitle(result.post) }}</strong>
          <StatusBadge :post="result.post" />
          <p class="text-muted">📍 {{ result.post.city }}</p>
        </div>
      </div>

      <div class="confirm-actions">
        <router-link class="btn btn-primary btn-lg btn-block" :to="result.post.url">Ver publicación</router-link>
        <ShareButtons
          :url="result.share_url"
          :title="`${meta?.emoji} ${postTitle(result.post)} — ${result.post.type_label} en ${result.post.city}`"
        />
      </div>

      <div v-if="result.manage_token" class="alert alert-warm manage-box">
        <div>
          <strong>Guarda este enlace privado</strong>
          <p class="small">
            Con él puedes editar tu publicación, cambiar su estado o cerrarla. No lo compartas: quien lo
            tenga puede administrarla.
          </p>
          <code class="manage-link">{{ result.manage_url }}</code>
          <div class="row">
            <router-link class="btn btn-ghost btn-sm" :to="`/gestionar/${result.manage_token}`">
              Administrar ahora
            </router-link>
            <router-link
              v-if="!auth.isAuthenticated"
              class="btn btn-primary btn-sm"
              :to="{ name: 'crear-cuenta', query: { vincular: result.manage_token } }"
            >
              Crear una cuenta y vincularla
            </router-link>
          </div>
        </div>
      </div>

      <p v-if="!auth.isAuthenticated && !result.manage_token" class="text-soft">
        ¿Quieres administrar fácilmente tus publicaciones?
        <router-link to="/crear-cuenta">Crea una cuenta</router-link>.
      </p>

      <button class="btn btn-quiet" type="button" @click="publishAnother">Publicar otra mascota</button>
    </div>
  </div>

  <div v-else class="container section publish">
    <header class="publish-head">
      <h1>Publicar una mascota</h1>
      <p class="text-soft">Solo te pediremos lo indispensable. Toma menos de dos minutos.</p>
    </header>

    <div class="stepper" role="group" aria-label="Progreso de la publicación">
      <div class="progress-track"><div class="progress-bar" :style="{ width: `${progress}%` }"></div></div>
      <ol class="steps">
        <li v-for="(nombre, index) in PASOS" :key="nombre">
          <button
            type="button"
            :class="{ 'is-current': index === step, 'is-done': index < step }"
            :disabled="index > step"
            @click="goTo(index)"
          >
            <span class="step-num">{{ index < step ? '✓' : index + 1 }}</span>
            <span class="step-name">{{ nombre }}</span>
          </button>
        </li>
      </ol>
    </div>

    <form class="panel" novalidate @submit.prevent="step === PASOS.length - 1 ? submit() : next()">
      <!-- Honeypot invisible contra bots -->
      <input v-model="form.website" class="honeypot" type="text" tabindex="-1" autocomplete="off" aria-hidden="true" />

      <!-- Paso 1: tipo -->
      <section v-if="step === 0" class="step">
        <h2>¿Qué quieres publicar?</h2>
        <div class="option-list">
          <button
            type="button"
            class="option"
            :class="{ 'is-selected': form.type === 'perdida' }"
            @click="form.type = 'perdida'"
          >
            <span class="emoji" aria-hidden="true">🔴</span>
            <span class="option-text">
              Perdí una mascota
              <span class="option-note">Estoy buscando a mi mascota</span>
            </span>
          </button>
          <button
            type="button"
            class="option"
            :class="{ 'is-selected': form.type === 'encontrada' }"
            @click="form.type = 'encontrada'"
          >
            <span class="emoji" aria-hidden="true">🟢</span>
            <span class="option-text">
              Encontré una mascota
              <span class="option-note">Quiero encontrar a su familia</span>
            </span>
          </button>
          <button
            type="button"
            class="option"
            :class="{ 'is-selected': form.type === 'adopcion' }"
            @click="form.type = 'adopcion'"
          >
            <span class="emoji" aria-hidden="true">💙</span>
            <span class="option-text">
              Mascota en adopción
              <span class="option-note">Busca un nuevo hogar</span>
            </span>
          </button>
        </div>
      </section>

      <!-- Paso 2: fotos -->
      <section v-else-if="step === 1" class="step">
        <h2>Agrega fotos</h2>
        <p class="text-soft">
          La foto es lo que más ayuda a identificar a una mascota. Puedes subir hasta 5.
        </p>
        <PhotoUploader v-model="form.photos" :max="ui.config?.max_photos || 5" />
      </section>

      <!-- Paso 3: la mascota -->
      <section v-else-if="step === 2" class="step">
        <h2>Sobre la mascota</h2>

        <div class="field">
          <span class="label">Especie</span>
          <div class="chip-group">
            <button
              v-for="especie in ESPECIES"
              :key="especie.value"
              type="button"
              class="chip"
              :class="{ 'is-selected': form.species === especie.value }"
              @click="form.species = especie.value"
            >
              {{ speciesEmoji(especie.value) }} {{ especie.label }}
            </button>
          </div>
        </div>

        <div class="field">
          <label class="label" for="description">Cuéntanos sobre la mascota</label>
          <textarea
            id="description"
            v-model="form.description"
            class="textarea"
            maxlength="2000"
            :placeholder="meta?.descriptionHint"
          ></textarea>
          <p class="hint">Ejemplo: «{{ meta?.descriptionHint }}»</p>
        </div>

        <button class="btn btn-quiet btn-sm optional-toggle" type="button" @click="showOptional = !showOptional">
          {{ showOptional ? '− Ocultar datos opcionales' : '+ Agregar más datos (opcional)' }}
        </button>

        <div v-if="showOptional" class="form-grid cols-2 optional-block">
          <div class="field">
            <label class="label" for="pet_name">Nombre <span class="optional">(opcional)</span></label>
            <input id="pet_name" v-model="form.pet_name" class="input" type="text" maxlength="80" />
          </div>
          <div class="field">
            <label class="label" for="breed">Raza <span class="optional">(opcional)</span></label>
            <input id="breed" v-model="form.breed" class="input" type="text" maxlength="80" />
          </div>
          <div class="field">
            <label class="label" for="color">Color <span class="optional">(opcional)</span></label>
            <input id="color" v-model="form.color" class="input" type="text" maxlength="80" />
          </div>
          <div class="field">
            <label class="label" for="age">Edad aproximada <span class="optional">(opcional)</span></label>
            <input id="age" v-model="form.age" class="input" type="text" maxlength="60" placeholder="Ej.: 2 años" />
          </div>
          <div class="field">
            <label class="label" for="sex">Sexo <span class="optional">(opcional)</span></label>
            <select id="sex" v-model="form.sex" class="select">
              <option value="">No lo sé</option>
              <option value="macho">Macho</option>
              <option value="hembra">Hembra</option>
            </select>
          </div>
          <div class="field">
            <label class="label" for="size">Tamaño <span class="optional">(opcional)</span></label>
            <select id="size" v-model="form.size" class="select">
              <option value="">No lo sé</option>
              <option value="pequeno">Pequeño</option>
              <option value="mediano">Mediano</option>
              <option value="grande">Grande</option>
            </select>
          </div>
          <div class="field field-full">
            <label class="switch-row">
              <span>Lleva collar</span>
              <input v-model="form.has_collar" type="checkbox" />
            </label>
            <label class="switch-row">
              <span>Lleva placa de identificación</span>
              <input v-model="form.has_tag" type="checkbox" />
            </label>
          </div>
          <div class="field field-full">
            <label class="label" for="marks">Características especiales <span class="optional">(opcional)</span></label>
            <textarea
              id="marks"
              v-model="form.special_marks"
              class="textarea"
              maxlength="500"
              placeholder="Manchas, cicatrices, cojera, oreja doblada…"
            ></textarea>
          </div>
        </div>
      </section>

      <!-- Paso 4: lugar y fecha -->
      <section v-else-if="step === 3" class="step">
        <h2>¿Dónde y cuándo?</h2>

        <div class="field">
          <span class="label">Ciudad</span>
          <CitySelect v-model="form.city" />
          <p class="hint">La ciudad es el filtro principal de búsqueda.</p>
        </div>

        <div class="field">
          <label class="label" for="event_date">{{ meta?.dateLabel }}</label>
          <input id="event_date" v-model="form.event_date" class="input" type="date" :max="todayISO()" />
        </div>

        <div class="field">
          <label class="label" for="neighborhood">Barrio o sector <span class="optional">(opcional)</span></label>
          <input
            id="neighborhood"
            v-model="form.neighborhood"
            class="input"
            type="text"
            maxlength="120"
            placeholder="Ej.: Palermo"
          />
        </div>

        <div class="field">
          <label class="label" for="address">Dirección <span class="optional">(opcional y privada)</span></label>
          <input id="address" v-model="form.address" class="input" type="text" maxlength="200" />
          <p class="hint">🔒 La dirección exacta nunca se muestra públicamente. Solo tú la ves.</p>
        </div>
      </section>

      <!-- Paso 5: contacto -->
      <section v-else-if="step === 4" class="step">
        <h2>¿Cómo te contactan?</h2>
        <p class="text-soft">Con un medio de contacto es suficiente. WhatsApp es el más rápido.</p>

        <div class="field">
          <label class="label" for="whatsapp">WhatsApp</label>
          <input
            id="whatsapp"
            v-model="form.contact_whatsapp"
            class="input"
            type="tel"
            inputmode="tel"
            maxlength="30"
            placeholder="Ej.: 310 123 4567"
          />
        </div>

        <div class="form-grid cols-2">
          <div class="field">
            <label class="label" for="phone">Teléfono <span class="optional">(opcional)</span></label>
            <input id="phone" v-model="form.contact_phone" class="input" type="tel" inputmode="tel" maxlength="30" />
          </div>
          <div class="field">
            <label class="label" for="contact_email">Correo <span class="optional">(opcional)</span></label>
            <input id="contact_email" v-model="form.contact_email" class="input" type="email" maxlength="255" />
          </div>
          <div class="field">
            <label class="label" for="contact_name">Tu nombre <span class="optional">(opcional)</span></label>
            <input id="contact_name" v-model="form.contact_name" class="input" type="text" maxlength="120" />
          </div>
          <div class="field">
            <label class="label" for="contact_note">Horario para contactarte <span class="optional">(opcional)</span></label>
            <input id="contact_note" v-model="form.contact_note" class="input" type="text" maxlength="200" />
          </div>
        </div>

        <div v-if="!auth.isAuthenticated" class="alert alert-info">
          <div>
            <strong>Publicas como invitado</strong>
            <p class="small">
              No necesitas crear una cuenta. Al terminar te daremos un enlace privado para administrar
              tu publicación. Si dejas tu correo, también podrás recuperarlo desde allí.
            </p>
          </div>
        </div>
      </section>

      <!-- Paso 6: revisar -->
      <section v-else class="step">
        <h2>Revisa antes de publicar</h2>

        <div class="review">
          <div class="review-photos">
            <img
              v-if="previewPost.photo_url"
              :src="previewPost.photo_url"
              alt="Foto principal"
              class="review-main"
            />
            <div v-if="form.photos.length > 1" class="review-thumbs">
              <img
                v-for="photo in form.photos.filter((p) => !p.is_primary)"
                :key="photo.url"
                :src="photo.url"
                alt="Foto adicional"
              />
            </div>
          </div>

          <dl class="review-data">
            <div><dt>Tipo</dt><dd>{{ meta?.emoji }} {{ meta?.label }}</dd></div>
            <div><dt>Especie</dt><dd>{{ speciesEmoji(form.species) }} {{ ESPECIES.find((e) => e.value === form.species)?.label }}</dd></div>
            <div v-if="form.pet_name"><dt>Nombre</dt><dd>{{ form.pet_name }}</dd></div>
            <div v-if="form.breed"><dt>Raza</dt><dd>{{ form.breed }}</dd></div>
            <div v-if="form.color"><dt>Color</dt><dd>{{ form.color }}</dd></div>
            <div>
              <dt>Ciudad</dt>
              <dd>{{ form.city?.city }}<template v-if="form.neighborhood"> · {{ form.neighborhood }}</template></dd>
            </div>
            <div><dt>Fecha</dt><dd>{{ formatDate(form.event_date) }}</dd></div>
            <div>
              <dt>Contacto</dt>
              <dd>
                <span v-if="form.contact_whatsapp">💬 {{ form.contact_whatsapp }}</span>
                <span v-if="form.contact_phone">📞 {{ form.contact_phone }}</span>
                <span v-if="form.contact_email">✉️ {{ form.contact_email }}</span>
              </dd>
            </div>
            <div class="full"><dt>Descripción</dt><dd>{{ form.description }}</dd></div>
          </dl>
        </div>
      </section>

      <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>

      <footer class="step-actions">
        <button v-if="step > 0" class="btn btn-ghost" type="button" @click="back">← Editar</button>
        <button v-if="step < PASOS.length - 1" class="btn btn-primary btn-lg" type="submit">
          Continuar →
        </button>
        <button v-else class="btn btn-primary btn-lg" type="submit" :disabled="sending">
          <span v-if="sending" class="spinner"></span>
          {{ sending ? 'Publicando…' : '🐾 Publicar' }}
        </button>
      </footer>
    </form>

    <p class="legal-note text-muted">
      Al publicar aceptas los <router-link to="/legal/terminos">términos y condiciones</router-link> y la
      <router-link to="/legal/privacidad">política de privacidad</router-link>.
    </p>
  </div>
</template>

<style scoped>
.publish-head { margin-bottom: 14px; }
.publish-head h1 { margin-bottom: 4px; }
.publish-head p { margin: 0; }

/* Progreso */
.stepper { margin-bottom: 16px; }

.progress-track {
  height: 6px;
  background: var(--surface-2);
  border-radius: var(--radius-pill);
  overflow: hidden;
  margin-bottom: 10px;
}
.progress-bar {
  height: 100%;
  background: var(--brand);
  border-radius: var(--radius-pill);
  transition: width 0.25s ease;
}

.steps {
  list-style: none;
  display: flex;
  gap: 4px;
  margin: 0;
  padding: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.steps::-webkit-scrollbar { display: none; }

.steps button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: none;
  background: none;
  border-radius: var(--radius-pill);
  color: var(--text-muted);
  font-size: 0.82rem;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
}
.steps button:disabled { cursor: default; }
.steps button.is-current { background: var(--brand-light); color: var(--brand-dark); }
.steps button.is-done { color: var(--brand); }

.step-num {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: currentColor;
  color: var(--surface);
  font-size: 0.7rem;
}

.step h2 { margin-top: 0; }

.optional-toggle { padding-inline: 0; }
.optional-block { margin-top: 10px; border-top: 1px dashed var(--border); padding-top: 14px; }

/* Revisión */
.review { display: grid; gap: 16px; }

.review-main {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border-radius: var(--radius);
}

.review-thumbs {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  margin-top: 6px;
}
.review-thumbs img {
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: var(--radius-sm);
}

.review-data { display: grid; gap: 10px; margin: 0; }
.review-data > div { display: grid; gap: 2px; }
.review-data dt { font-size: 0.8rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; }
.review-data dd { margin: 0; font-weight: 600; }
.review-data dd span { display: block; font-weight: 500; }
.review-data .full dd { font-weight: 400; white-space: pre-line; }

/* Acciones */
.step-actions {
  display: flex;
  flex-direction: column-reverse;
  gap: 10px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
.step-actions .btn { width: 100%; }

.legal-note { margin-top: 14px; text-align: center; font-size: 0.85rem; }

/* Confirmación */
.success-panel { display: grid; gap: 14px; justify-items: center; padding: 28px 18px; }
.success-emoji { font-size: 3rem; }
.success-panel h1 { margin: 0; }
.success-panel > p { margin: 0; max-width: 48ch; }

.preview-mini {
  display: flex;
  gap: 12px;
  align-items: center;
  width: 100%;
  padding: 12px;
  background: var(--surface-2);
  border-radius: var(--radius);
  text-align: left;
}
.preview-mini img { width: 72px; height: 72px; object-fit: cover; border-radius: var(--radius-sm); flex: none; }
.preview-mini div { display: grid; gap: 4px; justify-items: start; }
.preview-mini p { margin: 0; }

.confirm-actions { display: grid; gap: 10px; width: 100%; }

.manage-box { width: 100%; text-align: left; }
.manage-box p { margin: 4px 0 8px; }
.manage-link {
  display: block;
  word-break: break-all;
  background: rgba(255, 255, 255, 0.6);
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  font-size: 0.82rem;
  margin-bottom: 10px;
}

@media (min-width: 768px) {
  .publish { max-width: 760px; }
  .step-actions {
    flex-direction: row;
    justify-content: space-between;
  }
  .step-actions .btn { width: auto; min-width: 160px; }
  .step-actions .btn:only-child { margin-left: auto; }

  .review { grid-template-columns: 300px 1fr; align-items: start; }
  .review-data { grid-template-columns: 1fr 1fr; gap: 14px; }
  .review-data .full { grid-column: 1 / -1; }

  .steps button { font-size: 0.9rem; }
}
</style>
