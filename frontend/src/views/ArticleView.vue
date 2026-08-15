<script setup>
import { onMounted, ref } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import { api } from '@/api/client'
import { formatDate } from '@/lib/format'
import { setPageDescription, setPageTitle } from '@/lib/head'

const props = defineProps({
  slug: { type: String, required: true },
})

const article = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    article.value = await api.article(props.slug)
    setPageTitle(article.value.title)
    setPageDescription(article.value.excerpt || article.value.content)
  } catch {
    article.value = null
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="container section article-page">
    <p v-if="loading" class="text-soft">Cargando…</p>

    <EmptyState
      v-else-if="!article"
      emoji="📰"
      title="No encontramos este contenido"
      message="Puede que haya sido retirado o que el enlace esté incompleto."
    >
      <router-link class="btn btn-primary" to="/guias">Ver guías y ayuda</router-link>
    </EmptyState>

    <article v-else>
      <router-link class="btn btn-quiet btn-sm back" to="/guias">← Guías y ayuda</router-link>
      <h1>{{ article.title }}</h1>
      <p class="text-muted">
        {{ formatDate(article.published_at) }}
        <template v-if="article.city"> · 📍 {{ article.city }}</template>
      </p>

      <img v-if="article.image_url" :src="article.image_url" :alt="article.title" class="cover" />

      <div class="content">
        <p v-for="(parrafo, index) in article.content.split('\n\n')" :key="index">{{ parrafo }}</p>
      </div>

      <a v-if="article.contact_url" class="btn btn-primary" :href="article.contact_url" target="_blank" rel="noopener">
        Más información
      </a>
    </article>
  </div>
</template>

<style scoped>
.article-page { max-width: 760px; }
.back { padding-inline: 0; margin-bottom: 8px; }
.cover { width: 100%; border-radius: var(--radius-lg); margin: 16px 0; }
.content { font-size: 1.03rem; line-height: 1.7; }
.content p { white-space: pre-line; }
</style>
