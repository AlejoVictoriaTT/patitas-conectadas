<script setup>
/**
 * Emergencia: teléfonos, gobernaciones, alcaldías y entidades de atención.
 *
 * Está separada de las guías porque las dos cosas se buscan en momentos
 * distintos. Las guías se leen con calma, antes o después; esto se abre en
 * medio de una urgencia, y en ese momento cualquier contenido de más estorba.
 */
import { onMounted } from 'vue'
import EmergencyDirectory from '@/components/EmergencyDirectory.vue'
import { setPageDescription, setPageTitle } from '@/lib/head'

onMounted(() => {
  setPageTitle('Emergencia')
  setPageDescription(
    'Teléfonos de emergencia, gobernaciones, alcaldías y entidades de atención de los ' +
      'departamentos afectados por el terremoto.',
  )
})
</script>

<template>
  <div class="container section">
    <!-- El aviso va al lado del título, no debajo: es contexto del encabezado,
         y colgando aparte partía la lectura antes de llegar a los teléfonos. -->
    <header class="page-head">
      <div>
        <h1>Emergencia</h1>
        <p class="text-soft lead">
          A quién llamar y dónde consultar información oficial.
        </p>
      </div>

      <aside class="tip">
        <p>
          Guarda esta página o anota los números en un papel. En una emergencia la red móvil suele
          saturarse, y un número escrito a mano funciona cuando el celular no.
        </p>
      </aside>
    </header>

    <EmergencyDirectory />

    <div class="alert alert-info guides-link">
      <div>
        <strong>¿Buscas qué hacer paso a paso?</strong>
        <p class="small">
          Las guías para buscar una mascota perdida, ayudar a una que encontraste o preparar una
          adopción están en su propia sección.
        </p>
        <router-link class="btn btn-ghost btn-sm" to="/guias">Ver guías y consejos</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-head { display: grid; gap: 14px; margin-bottom: 22px; }
.page-head h1 { margin-bottom: 4px; }
.lead { margin: 0; max-width: 46ch; }

.tip {
  padding: 14px 16px;
  border-left: 4px solid var(--accent);
  border-radius: var(--radius);
  background: var(--accent-soft);
  color: #7c4a12;
}
.tip p { margin: 0; font-size: 0.92rem; line-height: 1.5; }

.guides-link { margin-top: 28px; }
.guides-link p { margin: 4px 0 10px; }

@media (min-width: 860px) {
  .page-head {
    grid-template-columns: 1fr minmax(280px, 400px);
    align-items: center;
    gap: 28px;
  }
}
</style>
