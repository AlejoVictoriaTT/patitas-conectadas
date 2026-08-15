<script setup>
import { onMounted, ref } from 'vue'
import PostManager from '@/components/PostManager.vue'
import EmptyState from '@/components/EmptyState.vue'
import { api } from '@/api/client'
import { postTitle } from '@/lib/format'
import { setPageTitle } from '@/lib/head'

const props = defineProps({
  id: { type: String, required: true },
})

const post = ref(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const data = await api.getPost(props.id)
    if (!data.is_owner) {
      error.value = 'No tienes permiso para administrar esta publicación.'
    } else {
      post.value = data
      setPageTitle(`Editar ${postTitle(data)}`)
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="container section">
    <p v-if="loading" class="text-soft">Cargando publicación…</p>

    <EmptyState v-else-if="error" emoji="🔒" title="No podemos abrir esta publicación" :message="error">
      <router-link class="btn btn-primary" to="/mis-publicaciones">Ver mis publicaciones</router-link>
    </EmptyState>

    <template v-else-if="post">
      <h1>Editar publicación</h1>
      <PostManager :post="post" @updated="post = $event" />
    </template>
  </div>
</template>
