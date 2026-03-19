<template>
  <div>
    <div class="page-head">
      <div class="page-head-text">
        <h2>Bibliothèque de services</h2>
        <p>Découvrez, téléchargez et activez des services pour votre infrastructure DataForge.</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="lib-toolbar">
      <div class="lib-search">
        <svg width="14" height="14" viewBox="0 0 15 15" fill="none">
          <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" stroke-width="1.3"/>
          <path d="M10 10l3 3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
        <input v-model="search" type="text" placeholder="Rechercher un service…" class="lib-search-input" />
      </div>

      <div class="lib-categories">
        <button
          v-for="cat in SERVICE_CATEGORIES"
          :key="cat.id"
          class="cat-btn"
          :class="{ active: selectedCategory === cat.id }"
          @click="selectedCategory = cat.id"
        >{{ cat.label }}</button>
      </div>
    </div>

    <!-- Grid -->
    <div v-if="filtered.length" class="lib-grid">
      <ServiceCard
        v-for="svc in filtered"
        :key="svc.id"
        :service="svc"
        :enabled="libraryStore.isEnabled(svc.id)"
        :pull-status="libraryStore.pullStatus[svc.dockerImage] || 'unknown'"
        @action="handleAction"
      />
    </div>
    <div v-else class="lib-empty">
      <p>Aucun service ne correspond à votre recherche.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { SERVICES, SERVICE_CATEGORIES } from '../data/services.js'
import { useLibraryStore } from '../stores/library.js'
import { useToastStore } from '../stores/toast.js'
import ServiceCard from '../components/library/ServiceCard.vue'

const libraryStore = useLibraryStore()
const toastStore = useToastStore()

const search = ref('')
const selectedCategory = ref('all')

const filtered = computed(() => {
  let list = SERVICES
  if (selectedCategory.value !== 'all') {
    list = list.filter(s => s.category === selectedCategory.value)
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(s =>
      s.name.toLowerCase().includes(q) ||
      s.description.toLowerCase().includes(q) ||
      s.tags.some(t => t.includes(q)) ||
      s.dockerImage.toLowerCase().includes(q)
    )
  }
  return list
})

async function handleAction(service) {
  const status = libraryStore.pullStatus[service.dockerImage]
  const isEnabled = libraryStore.isEnabled(service.id)

  if (isEnabled) {
    // Retirer
    await libraryStore.setEnabled(service.id, false)
    toastStore.show(`${service.name} retiré de vos services`, 'info')
  } else if (status === 'pulled') {
    // Image déjà téléchargée → juste activer
    await libraryStore.setEnabled(service.id, true)
    toastStore.show(`${service.name} ajouté à vos services`, 'success')
  } else {
    // Télécharger + activer
    try {
      await libraryStore.pullImage(service.id)
      toastStore.show(`Téléchargement de ${service.name} lancé…`, 'info')
      await libraryStore.setEnabled(service.id, true)
    } catch {
      toastStore.show(`Erreur lors du téléchargement de ${service.name}`, 'error')
    }
  }
}

onMounted(async () => {
  await Promise.all([
    libraryStore.loadEnabled(),
    libraryStore.loadPullStatus(),
  ])
  // Resume polling if any image is still pulling
  const stillPulling = Object.values(libraryStore.pullStatus).some(s => s === 'pulling')
  if (stillPulling) libraryStore.startPolling()
})
</script>

<style scoped>
.lib-toolbar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.lib-search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--white);
  border: 1.5px solid var(--border);
  border-radius: 8px;
  padding: 0 12px;
  max-width: 380px;
  color: var(--text-muted);
}
.lib-search-input {
  border: none; outline: none; background: transparent;
  font-size: 13.5px; color: var(--text-primary); padding: 9px 0;
  width: 100%; font-family: inherit;
}
.lib-search-input::placeholder { color: var(--text-muted); }

.lib-categories {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.cat-btn {
  font-size: 12.5px; font-weight: 500;
  padding: 5px 14px; border-radius: 20px;
  border: 1.5px solid var(--border);
  background: var(--white); color: var(--text-secondary);
  cursor: pointer; transition: all 0.12s; font-family: inherit;
}
.cat-btn:hover { border-color: var(--accent); color: var(--accent); }
.cat-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }

.lib-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.lib-empty {
  text-align: center; padding: 60px 20px;
  color: var(--text-muted); font-size: 14px;
}
</style>
