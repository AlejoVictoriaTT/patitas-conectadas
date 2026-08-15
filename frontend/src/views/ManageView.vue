<script setup>
import { onMounted, ref } from 'vue'
import PostManager from '@/components/PostManager.vue'
import EmptyState from '@/components/EmptyState.vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { postTitle } from '@/lib/format'
import { setPageTitle } from '@/lib/head'

const props = defineProps({
  token: { type: String, required: true },
})

const auth = useAuthStore()
const ui = useUiStore()

const post = ref(null)
const loading = ref(true)
const error = ref('')
const linking = ref(false)

async function load() {
  loading.value = true
  try {
    post.value = await api.getByManageToken(props.token)
    setPageTitle(`Administrar ${postTitle(post.value)}`)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function linkToAccount() {
  linking.value = true
  try {
    await api.claimPost(props.token)
    ui.success('Publicación vinculada a tu cuenta. Ya la verás en «Mis publicaciones».')
    await load()
  } catch (err) {
    ui.error(err.message)
  } finally {
    linking.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="container section">
    <p v-if="loading" class="text-soft">Cargando publicación…</p>

    <EmptyState
      v-else-if="error"
      emoji="🔑"
      title="Este enlace no es válido"
      :message="error"
    >
      <router-link class="btn btn-primary" to="/">Ir al inicio</router-link>
    </EmptyState>

    <template v-else-if="post">
      <header class="head">
        <h1>Administrar publicación</h1>
        <p class="text-soft">
          Llegaste con tu enlace privado. Guárdalo para volver a entrar cuando lo necesites.
        </p>
      </header>

      <div v-if="auth.isAuthenticated && !post.has_account_owner" class="alert alert-info link-box">
        <div>
          <strong>Vincula esta publicación a tu cuenta</strong>
          <p class="small">Así podrás administrarla desde «Mis publicaciones» sin usar el enlace.</p>
          <button class="btn btn-primary btn-sm" type="button" :disabled="linking" @click="linkToAccount">
            {{ linking ? 'Vinculando…' : 'Vincular a mi cuenta' }}
          </button>
        </div>
      </div>

      <div v-else-if="!auth.isAuthenticated" class="alert alert-warm link-box">
        <div>
          <strong>¿Quieres administrar fácilmente tus publicaciones?</strong>
          <p class="small">
            Crea una cuenta gratis y vincula esta publicación para no depender del enlace privado.
          </p>
          <router-link class="btn btn-primary btn-sm" :to="{ name: 'crear-cuenta', query: { vincular: token } }">
            Crear una cuenta
          </router-link>
        </div>
      </div>

      <PostManager :post="post" :manage-token="token" @updated="post = $event" />
    </template>
  </div>
</template>

<style scoped>
.head { margin-bottom: 16px; }
.head h1 { margin-bottom: 4px; }
.head p { margin: 0; }
.link-box { margin-bottom: 16px; }
.link-box p { margin: 4px 0 10px; }
</style>
