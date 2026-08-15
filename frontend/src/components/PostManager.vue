<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import CitySelect from '@/components/CitySelect.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import ShareButtons from '@/components/ShareButtons.vue'
import { compressImage } from '@/lib/image'
import { api } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { postTitle, typeMeta } from '@/lib/format'

const props = defineProps({
  post: { type: Object, required: true },
  manageToken: { type: String, default: '' },
})

const emit = defineEmits(['updated', 'deleted'])

const router = useRouter()
const ui = useUiStore()

const saving = ref(false)
const busyPhoto = ref(false)
const confirmDelete = ref(false)
const fileInput = ref(null)

const token = computed(() => props.manageToken || undefined)
const meta = computed(() => typeMeta(props.post.type))
const shareUrl = computed(() => `${window.location.origin}${props.post.url}`)

const ESTADOS = computed(() => {
  const opciones = {
    perdida: [
      { value: 'perdida', label: '🔴 Sigue perdida' },
      { value: 'reunida', label: '🟢 ¡Ya está con su familia!' },
      { value: 'cerrada', label: '⚫ Cerrar el caso' },
    ],
    encontrada: [
      { value: 'buscando_familia', label: '🟢 Sigue buscando a su familia' },
      { value: 'entregada', label: '🏠 Entregada a su familia' },
      { value: 'cerrada', label: '⚫ Cerrar el caso' },
    ],
    adopcion: [
      { value: 'disponible', label: '💙 Disponible para adopción' },
      { value: 'adoptada', label: '🏠 Ya fue adoptada' },
      { value: 'cerrada', label: '⚫ Cerrar la publicación' },
    ],
  }
  return opciones[props.post.type] || []
})

const form = reactive({
  pet_name: '',
  breed: '',
  color: '',
  age: '',
  sex: '',
  size: '',
  special_marks: '',
  description: '',
  event_date: '',
  city: null,
  neighborhood: '',
  address: '',
  contact_name: '',
  contact_whatsapp: '',
  contact_phone: '',
  contact_email: '',
  contact_note: '',
})

function hydrate(post) {
  form.pet_name = post.pet_name || ''
  form.breed = post.breed || ''
  form.color = post.color || ''
  form.age = post.age || ''
  form.sex = post.sex || ''
  form.size = post.size || ''
  form.special_marks = post.special_marks || ''
  form.description = post.description || ''
  form.event_date = post.event_date || ''
  form.city = { country: post.location.country, region: post.location.region, city: post.location.city }
  form.neighborhood = post.location.neighborhood || ''
  form.address = post.location.address || ''
  form.contact_name = post.contact.name || ''
  form.contact_whatsapp = post.contact.whatsapp || ''
  form.contact_phone = post.contact.phone || ''
  form.contact_email = post.contact.email || ''
  form.contact_note = post.contact.note || ''
}

watch(() => props.post, hydrate, { immediate: true })

async function save() {
  saving.value = true
  try {
    const updated = await api.updatePost(
      props.post.id,
      {
        pet_name: form.pet_name.trim() || null,
        breed: form.breed.trim() || null,
        color: form.color.trim() || null,
        age: form.age.trim() || null,
        sex: form.sex || null,
        size: form.size || null,
        special_marks: form.special_marks.trim() || null,
        description: form.description.trim(),
        event_date: form.event_date,
        location: {
          country: form.city?.country || 'Colombia',
          region: form.city?.region || null,
          city: form.city?.city,
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
      },
      token.value,
    )
    emit('updated', updated)
    ui.success('Cambios guardados.')
  } catch (error) {
    ui.error(error.message)
  } finally {
    saving.value = false
  }
}

async function changeStatus(value) {
  if (value === props.post.status) return
  try {
    const updated = await api.changeStatus(props.post.id, value, token.value)
    emit('updated', updated)
    ui.success('Estado actualizado.')
  } catch (error) {
    ui.error(error.message)
  }
}

async function addPhotos(event) {
  const input = event.target
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length) return

  busyPhoto.value = true
  try {
    const nuevos = []
    for (const file of files.slice(0, 5 - props.post.photos.length)) {
      const optimized = await compressImage(file)
      const { url } = await api.upload(optimized)
      nuevos.push({ url, is_primary: false })
    }
    if (nuevos.length) {
      emit('updated', await api.addPhotos(props.post.id, nuevos, token.value))
      ui.success('Foto agregada.')
    }
  } catch (error) {
    ui.error(error.message)
  } finally {
    busyPhoto.value = false
  }
}

async function setPrimary(photoId) {
  busyPhoto.value = true
  try {
    emit('updated', await api.setPrimaryPhoto(props.post.id, photoId, token.value))
  } catch (error) {
    ui.error(error.message)
  } finally {
    busyPhoto.value = false
  }
}

async function removePhoto(photoId) {
  busyPhoto.value = true
  try {
    emit('updated', await api.deletePhoto(props.post.id, photoId, token.value))
  } catch (error) {
    ui.error(error.message)
  } finally {
    busyPhoto.value = false
  }
}

async function movePhoto(index, delta) {
  const ids = props.post.photos.map((p) => p.id)
  const target = index + delta
  if (target < 0 || target >= ids.length) return
  const [item] = ids.splice(index, 1)
  ids.splice(target, 0, item)
  busyPhoto.value = true
  try {
    emit('updated', await api.reorderPhotos(props.post.id, ids, token.value))
  } catch (error) {
    ui.error(error.message)
  } finally {
    busyPhoto.value = false
  }
}

async function removePost() {
  try {
    await api.deletePost(props.post.id, token.value)
    if (props.manageToken) ui.forgetGuestPost(props.manageToken)
    ui.success('Publicación eliminada.')
    emit('deleted')
    router.push('/')
  } catch (error) {
    ui.error(error.message)
  }
}
</script>

<template>
  <div class="manager stack-lg">
    <!-- Resumen -->
    <section class="panel summary">
      <div class="summary-main">
        <img v-if="post.photo_url" :src="post.photo_url" alt="Foto principal" />
        <div>
          <h2>{{ postTitle(post) }}</h2>
          <div class="row-tight">
            <StatusBadge :post="post" variant="type" />
            <StatusBadge :post="post" />
          </div>
          <p class="text-muted">📍 {{ post.city }} · 👁️ {{ post.views }} visitas</p>
        </div>
      </div>
      <router-link class="btn btn-ghost btn-sm" :to="post.url">Ver publicación pública</router-link>
    </section>

    <!-- Estado -->
    <section class="panel">
      <h2>Estado de la publicación</h2>
      <p class="text-soft small">
        Cuando el caso se resuelva, actualiza el estado. La publicación no se borra: queda como
        historia con un mensaje de buenas noticias.
      </p>
      <div class="option-list">
        <button
          v-for="estado in ESTADOS"
          :key="estado.value"
          type="button"
          class="option"
          :class="{ 'is-selected': post.status === estado.value }"
          @click="changeStatus(estado.value)"
        >
          {{ estado.label }}
        </button>
      </div>
    </section>

    <!-- Fotos -->
    <section class="panel">
      <h2>Fotos</h2>
      <div class="thumbs">
        <figure v-for="(photo, index) in post.photos" :key="photo.id" :class="{ 'is-primary': photo.is_primary }">
          <img :src="photo.url" :alt="`Foto ${index + 1}`" />
          <span v-if="photo.is_primary" class="primary-flag">⭐ Principal</span>
          <figcaption>
            <button
              v-if="!photo.is_primary"
              type="button"
              title="Establecer como principal"
              :disabled="busyPhoto"
              @click="setPrimary(photo.id)"
            >⭐</button>
            <button type="button" title="Mover antes" :disabled="busyPhoto || index === 0" @click="movePhoto(index, -1)">←</button>
            <button
              type="button"
              title="Mover después"
              :disabled="busyPhoto || index === post.photos.length - 1"
              @click="movePhoto(index, 1)"
            >→</button>
            <button
              type="button"
              class="danger"
              title="Eliminar"
              :disabled="busyPhoto || post.photos.length <= 1"
              @click="removePhoto(photo.id)"
            >🗑️</button>
          </figcaption>
        </figure>
      </div>

      <button
        v-if="post.photos.length < 5"
        class="btn btn-ghost btn-block"
        type="button"
        :disabled="busyPhoto"
        @click="fileInput.click()"
      >
        {{ busyPhoto ? 'Procesando…' : '📷 Agregar foto' }}
      </button>
      <input
        ref="fileInput"
        class="sr-only"
        type="file"
        accept="image/jpeg,image/png,image/webp,image/heic"
        multiple
        @change="addPhotos"
      />
    </section>

    <!-- Datos -->
    <form class="panel" @submit.prevent="save">
      <h2>Información</h2>

      <div class="field">
        <label class="label" for="m-description">Descripción</label>
        <textarea id="m-description" v-model="form.description" class="textarea" maxlength="2000"></textarea>
      </div>

      <div class="form-grid cols-2">
        <div class="field">
          <label class="label" for="m-name">Nombre</label>
          <input id="m-name" v-model="form.pet_name" class="input" type="text" maxlength="80" />
        </div>
        <div class="field">
          <label class="label" for="m-breed">Raza</label>
          <input id="m-breed" v-model="form.breed" class="input" type="text" maxlength="80" />
        </div>
        <div class="field">
          <label class="label" for="m-color">Color</label>
          <input id="m-color" v-model="form.color" class="input" type="text" maxlength="80" />
        </div>
        <div class="field">
          <label class="label" for="m-age">Edad aproximada</label>
          <input id="m-age" v-model="form.age" class="input" type="text" maxlength="60" />
        </div>
        <div class="field">
          <label class="label" for="m-sex">Sexo</label>
          <select id="m-sex" v-model="form.sex" class="select">
            <option value="">No lo sé</option>
            <option value="macho">Macho</option>
            <option value="hembra">Hembra</option>
          </select>
        </div>
        <div class="field">
          <label class="label" for="m-size">Tamaño</label>
          <select id="m-size" v-model="form.size" class="select">
            <option value="">No lo sé</option>
            <option value="pequeno">Pequeño</option>
            <option value="mediano">Mediano</option>
            <option value="grande">Grande</option>
          </select>
        </div>
        <div class="field field-full">
          <label class="label" for="m-marks">Características especiales</label>
          <textarea id="m-marks" v-model="form.special_marks" class="textarea" maxlength="500"></textarea>
        </div>
      </div>

      <h2>Lugar y fecha</h2>
      <div class="form-grid cols-2">
        <div class="field">
          <span class="label">Ciudad</span>
          <CitySelect v-model="form.city" />
        </div>
        <div class="field">
          <label class="label" for="m-date">{{ meta.dateLabel }}</label>
          <input id="m-date" v-model="form.event_date" class="input" type="date" />
        </div>
        <div class="field">
          <label class="label" for="m-neighborhood">Barrio o sector</label>
          <input id="m-neighborhood" v-model="form.neighborhood" class="input" type="text" maxlength="120" />
        </div>
        <div class="field">
          <label class="label" for="m-address">Dirección <span class="optional">(privada)</span></label>
          <input id="m-address" v-model="form.address" class="input" type="text" maxlength="200" />
        </div>
      </div>

      <h2>Contacto</h2>
      <div class="form-grid cols-2">
        <div class="field">
          <label class="label" for="m-wa">WhatsApp</label>
          <input id="m-wa" v-model="form.contact_whatsapp" class="input" type="tel" maxlength="30" />
        </div>
        <div class="field">
          <label class="label" for="m-phone">Teléfono</label>
          <input id="m-phone" v-model="form.contact_phone" class="input" type="tel" maxlength="30" />
        </div>
        <div class="field">
          <label class="label" for="m-email">Correo</label>
          <input id="m-email" v-model="form.contact_email" class="input" type="email" maxlength="255" />
        </div>
        <div class="field">
          <label class="label" for="m-contact-name">Nombre de contacto</label>
          <input id="m-contact-name" v-model="form.contact_name" class="input" type="text" maxlength="120" />
        </div>
        <div class="field field-full">
          <label class="label" for="m-note">Horario para contactarte</label>
          <input id="m-note" v-model="form.contact_note" class="input" type="text" maxlength="200" />
        </div>
      </div>

      <button class="btn btn-primary btn-lg btn-block" type="submit" :disabled="saving">
        <span v-if="saving" class="spinner"></span>
        {{ saving ? 'Guardando…' : 'Guardar cambios' }}
      </button>
    </form>

    <!-- Compartir -->
    <section class="panel">
      <h2>📤 Compartir</h2>
      <ShareButtons
        :url="shareUrl"
        :title="`${meta.emoji} ${postTitle(post)} — ${post.type_label} en ${post.city}`"
      />
    </section>

    <!-- Eliminar -->
    <section class="panel danger-zone">
      <h2>Eliminar publicación</h2>
      <p class="text-soft small">
        Si prefieres cerrarla en lugar de borrarla, cambia el estado a «Caso cerrado»: así queda el
        registro y las fotos siguen ayudando a otras personas.
      </p>
      <button v-if="!confirmDelete" class="btn btn-danger" type="button" @click="confirmDelete = true">
        Eliminar definitivamente
      </button>
      <div v-else class="row">
        <button class="btn btn-danger" type="button" @click="removePost">Sí, eliminar</button>
        <button class="btn btn-ghost" type="button" @click="confirmDelete = false">Cancelar</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.panel h2 { font-size: 1.05rem; margin-top: 0; }
.panel h2:not(:first-child) { margin-top: 18px; }

.summary { display: grid; gap: 12px; }
.summary-main { display: flex; gap: 12px; align-items: center; }
.summary-main img { width: 84px; height: 84px; object-fit: cover; border-radius: var(--radius); flex: none; }
.summary-main h2 { margin: 0 0 6px; }
.summary-main p { margin: 6px 0 0; }

.thumbs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.thumbs figure {
  position: relative;
  margin: 0;
  aspect-ratio: 1;
  border-radius: var(--radius);
  overflow: hidden;
  border: 2px solid var(--border);
}
.thumbs figure.is-primary { border-color: var(--brand); }
.thumbs img { width: 100%; height: 100%; object-fit: cover; }

.primary-flag {
  position: absolute;
  top: 5px;
  left: 5px;
  background: var(--brand);
  color: #fff;
  font-size: 0.68rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: var(--radius-pill);
}

.thumbs figcaption {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  justify-content: center;
  gap: 3px;
  padding: 5px 3px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.6));
}

.thumbs figcaption button {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  cursor: pointer;
  font-size: 0.8rem;
}
.thumbs figcaption button:disabled { opacity: 0.4; cursor: not-allowed; }
.thumbs figcaption button.danger { background: rgba(255, 226, 226, 0.95); }

.danger-zone { border-color: #f3d2d2; }

@media (min-width: 480px) {
  .thumbs { grid-template-columns: repeat(5, 1fr); }
}

@media (min-width: 768px) {
  .summary { grid-template-columns: 1fr auto; align-items: center; }
}
</style>
