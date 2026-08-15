<script setup>
/**
 * Directorio de emergencia.
 *
 * Está en el frontend, como dato estático, y no en la base de datos, por una
 * razón concreta: es información que tiene que estar disponible sí o sí. Si la
 * API está caída justo cuando alguien la necesita, esta sección sigue
 * apareciendo porque viaja dentro de la propia página.
 *
 * Los enlaces oficiales se verificaron uno por uno. Los que solo responden por
 * HTTP o que redirigen están anotados donde corresponde. Conviene revisarlos
 * cada cierto tiempo: los sitios de las alcaldías cambian de dominio con
 * frecuencia.
 */

const LINEAS_NACIONALES = [
  {
    numero: '123',
    nombre: 'Línea única de emergencias',
    detalle: 'Policía, ambulancia y bomberos. Es la primera llamada en cualquier emergencia.',
  },
  {
    numero: '119',
    nombre: 'Bomberos',
    detalle: 'Incendios, rescates y estructuras colapsadas.',
  },
  {
    numero: '144',
    nombre: 'Defensa Civil Colombiana',
    detalle: 'Búsqueda, rescate y atención en desastres.',
  },
  {
    numero: '132',
    nombre: 'Cruz Roja Colombiana',
    detalle: 'Atención prehospitalaria y ayuda humanitaria.',
  },
  {
    numero: '125',
    nombre: 'Emergencias médicas',
    detalle: 'Ambulancias en la mayoría de municipios.',
  },
]

// Departamentos afectados por el terremoto del 10 de agosto de 2026, con su capital.
const DEPARTAMENTOS = [
  {
    nombre: 'Valle del Cauca',
    capital: 'Cali',
    gobernacion: 'https://www.valledelcauca.gov.co',
    alcaldia: 'https://www.cali.gov.co',
  },
  {
    nombre: 'Risaralda',
    capital: 'Pereira',
    gobernacion: 'https://www.risaralda.gov.co',
    alcaldia: 'https://www.pereira.gov.co',
  },
  {
    nombre: 'Caldas',
    capital: 'Manizales',
    gobernacion: 'https://www.caldas.gov.co',
    alcaldia: 'https://www.manizales.gov.co',
  },
  {
    nombre: 'Quindío',
    capital: 'Armenia',
    gobernacion: 'https://www.quindio.gov.co',
    alcaldia: 'https://www.armenia.gov.co',
  },
  {
    nombre: 'Chocó',
    capital: 'Quibdó',
    // El sitio de la Gobernación del Chocó solo responde por HTTP, sin certificado.
    gobernacion: 'http://www.choco.gov.co',
    alcaldia: 'https://www.quibdo-choco.gov.co',
  },
]

const ENTIDADES = [
  {
    nombre: 'UNGRD',
    descripcion: 'Unidad Nacional para la Gestión del Riesgo de Desastres. Boletines oficiales de la emergencia.',
    url: 'https://www.gestiondelriesgo.gov.co',
  },
  {
    nombre: 'Servicio Geológico Colombiano',
    descripcion: 'Reportes de sismos y réplicas en tiempo real.',
    url: 'https://www.sgc.gov.co',
  },
  {
    nombre: 'Defensa Civil Colombiana',
    descripcion: 'Sedes por departamento y canales de voluntariado.',
    url: 'https://www.defensacivil.gov.co',
  },
  {
    nombre: 'Cruz Roja Colombiana',
    descripcion: 'Donaciones y puntos de atención humanitaria.',
    url: 'https://www.cruzrojacolombiana.org',
  },
  {
    nombre: 'Dirección Nacional de Bomberos',
    descripcion: 'Directorio de cuerpos de bomberos del país.',
    url: 'https://dnbc.gov.co',
  },
]
</script>

<template>
  <section class="emergency">
    <!-- Líneas nacionales -->
    <div class="panel lines-panel">
      <h3>Líneas nacionales</h3>
      <ul class="lines">
        <li v-for="linea in LINEAS_NACIONALES" :key="linea.numero">
          <a :href="`tel:${linea.numero}`" class="line-number">{{ linea.numero }}</a>
          <div class="line-text">
            <strong>{{ linea.nombre }}</strong>
            <span class="text-soft small">{{ linea.detalle }}</span>
          </div>
        </li>
      </ul>
      <p class="text-muted small note">
        Los números son de tres dígitos y funcionan desde cualquier operador, incluso sin saldo.
      </p>
    </div>

    <!-- Gobernaciones y alcaldías -->
    <div class="panel">
      <h3>Gobernaciones y alcaldías</h3>
      <p class="text-soft small intro">
        Departamentos afectados por el terremoto del 10 de agosto de 2026. Ahí se publican los
        albergues habilitados, los censos de damnificados y las ayudas disponibles.
      </p>

      <ul class="places">
        <li v-for="dep in DEPARTAMENTOS" :key="dep.nombre">
          <span class="place-name">{{ dep.nombre }}</span>
          <span class="place-links">
            <a :href="dep.gobernacion" target="_blank" rel="noopener noreferrer">Gobernación</a>
            <a :href="dep.alcaldia" target="_blank" rel="noopener noreferrer">
              Alcaldía de {{ dep.capital }}
            </a>
          </span>
        </li>
      </ul>
    </div>

    <!-- Entidades nacionales -->
    <div class="panel">
      <h3>Entidades de atención</h3>
      <ul class="entities">
        <li v-for="entidad in ENTIDADES" :key="entidad.nombre">
          <a :href="entidad.url" target="_blank" rel="noopener noreferrer">
            <strong>{{ entidad.nombre }}</strong>
            <span class="external" aria-hidden="true">↗</span>
          </a>
          <span class="text-soft small">{{ entidad.descripcion }}</span>
        </li>
      </ul>
    </div>

    <div class="alert alert-warm pets-note">
      <div>
        <strong>Si tu mascota se perdió durante la emergencia</strong>
        <p class="small">
          Publícala aquí con una foto y el sector donde estaba. Muchos animales aparecen a pocas
          cuadras, y varios albergues de la zona están recibiendo animales rescatados mientras
          buscan a sus familias.
        </p>
        <router-link class="btn btn-primary btn-sm" :to="{ path: '/publicar', query: { tipo: 'perdida' } }">
          Publicar una mascota perdida
        </router-link>
      </div>
    </div>
  </section>
</template>

<style scoped>
.emergency { display: grid; gap: 14px; }

.panel h3 { margin-top: 0; font-size: 1.02rem; }
.intro { margin: -4px 0 12px; max-width: 62ch; }
.note { margin: 12px 0 0; }

/* ------------------------------------------------------- líneas nacionales */

.lines-panel { border-color: var(--border-strong); }

.lines {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.lines li {
  display: flex;
  align-items: center;
  gap: 14px;
}

/* El número es el elemento más importante de la sección: grande, tocable y
   marcable de un toque desde el celular. */
.line-number {
  flex: none;
  display: grid;
  place-items: center;
  min-width: 74px;
  min-height: var(--tap);
  padding: 6px 12px;
  border-radius: var(--radius);
  background: var(--perdida-soft);
  color: #b42318;
  font-size: 1.35rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
  transition:
    background var(--dur) var(--ease-out),
    transform var(--dur-fast) var(--ease-out);
}
.line-number:hover {
  text-decoration: none;
  background: #fbdada;
  transform: translateY(-1px);
}

.line-text { display: grid; gap: 1px; min-width: 0; }

/* ------------------------------------------------- gobernaciones y alcaldías */

.places {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.places li {
  display: grid;
  gap: 4px;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--border);
}
.places li:last-child { border-bottom: none; padding-bottom: 0; }

.place-name { font-weight: 700; }
.place-links { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 0.92rem; }

/* ------------------------------------------------------------- entidades */

.entities {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.entities li { display: grid; gap: 2px; }
.entities a { display: inline-flex; align-items: center; gap: 6px; }
.external { opacity: 0.6; font-size: 0.85em; }

.pets-note p { margin: 4px 0 10px; }

@media (min-width: 640px) {
  .places li {
    grid-template-columns: minmax(140px, 1fr) 2fr;
    align-items: baseline;
    gap: 12px;
  }
}

@media (min-width: 900px) {
  .lines { grid-template-columns: 1fr 1fr; gap: 12px 24px; }
  .entities { grid-template-columns: 1fr 1fr; gap: 14px 28px; }
}
</style>
