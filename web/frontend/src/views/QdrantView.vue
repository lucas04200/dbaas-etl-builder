<template>
  <div>
    <div class="page-head">
      <div class="page-head-text">
        <h2>Qdrant</h2>
        <p>Gérez vos instances de base de données vectorielle</p>
      </div>
      <button v-if="isAdmin" class="btn btn-primary" @click="showCreateModal = true">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
          <line x1="6.5" y1="1" x2="6.5" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="1" y1="6.5" x2="12" y2="6.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        Nouvelle instance
      </button>
    </div>

    <div v-if="loading" class="loading">Chargement…</div>
    <div v-else-if="!instances.length" class="empty" style="padding:40px 0;text-align:center">
      Aucune instance Qdrant déployée.
    </div>
    <div v-else class="instance-grid">
      <QdrantCard
        v-for="inst in instances"
        :key="inst.id"
        :instance="inst"
        @delete="deleteInstance"
      />
    </div>

    <CreateQdrantModal v-model="showCreateModal" @created="loadInstances" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import { useToastStore } from '../stores/toast.js'
import { apiGetQdrant, apiGetQdrantInstance, apiDeleteQdrant } from '../lib/api.js'
import QdrantCard from '../components/qdrant/QdrantCard.vue'
import CreateQdrantModal from '../components/qdrant/CreateQdrantModal.vue'

const authStore = useAuthStore()
const toastStore = useToastStore()

const instances = ref([])
const loading = ref(true)
const showCreateModal = ref(false)
const pollTimers = {}

const isAdmin = computed(() => authStore.currentUser?.role === 'admin')

async function loadInstances() {
  const res = await apiGetQdrant()
  if (!res || !res.ok) {
    loading.value = false
    return
  }
  instances.value = await res.json()
  loading.value = false

  instances.value.filter(i => i.status === 'provisioning').forEach(i => {
    const key = `qdrant-${i.id}`
    if (!pollTimers[key]) {
      pollTimers[key] = setInterval(() => pollStatus(i.id), 5000)
    }
  })
}

async function pollStatus(id) {
  const res = await apiGetQdrantInstance(id)
  if (!res || !res.ok) return
  const inst = await res.json()
  if (inst.status !== 'provisioning') {
    const key = `qdrant-${id}`
    clearInterval(pollTimers[key])
    delete pollTimers[key]
    const idx = instances.value.findIndex(i => i.id === id)
    if (idx !== -1) instances.value[idx] = { ...instances.value[idx], ...inst }
    if (inst.status === 'error') toastStore.showToast('Erreur lors du provisionnement Qdrant', true)
  }
}

async function deleteInstance(instance) {
  if (!confirm(`Supprimer l'instance Qdrant « ${instance.name} » ?`)) return
  const res = await apiDeleteQdrant(instance.id)
  if (res && res.ok) {
    toastStore.showToast('Instance Qdrant supprimée')
    await loadInstances()
  } else {
    const d = await res?.json().catch(() => ({}))
    toastStore.showToast(d.detail || 'Erreur', true)
  }
}

onMounted(loadInstances)

onUnmounted(() => {
  Object.values(pollTimers).forEach(clearInterval)
})
</script>
