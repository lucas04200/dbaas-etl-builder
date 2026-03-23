<template>
  <div>
    <div class="page-head">
      <div class="page-head-text">
        <h2>Mage.ai</h2>
        <p>Gérez vos instances de pipelines ETL</p>
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
      Aucune instance Mage déployée.
    </div>
    <div v-else class="instance-grid">
      <MageCard
        v-for="inst in instances"
        :key="inst.id"
        :instance="inst"
        @delete="deleteInstance"
      />
    </div>

    <CreateMageModal v-model="showCreateModal" @created="loadInstances" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import { useToastStore } from '../stores/toast.js'
import { apiGetMage, apiGetMageInstance, apiDeleteMage } from '../lib/api.js'
import MageCard from '../components/mage/MageCard.vue'
import CreateMageModal from '../components/mage/CreateMageModal.vue'

const authStore = useAuthStore()
const toastStore = useToastStore()

const instances = ref([])
const loading = ref(true)
const showCreateModal = ref(false)
const pollTimers = {}

const isAdmin = computed(() => authStore.currentUser?.role === 'admin')

async function loadInstances() {
  const res = await apiGetMage()
  if (!res || !res.ok) {
    loading.value = false
    return
  }
  instances.value = await res.json()
  loading.value = false

  instances.value.filter(i => i.status === 'provisioning').forEach(i => {
    const key = `mage-${i.id}`
    if (!pollTimers[key]) {
      pollTimers[key] = setInterval(() => pollStatus(i.id), 5000)
    }
  })
}

async function pollStatus(id) {
  const res = await apiGetMageInstance(id)
  if (!res || !res.ok) return
  const inst = await res.json()
  if (inst.status !== 'provisioning') {
    const key = `mage-${id}`
    clearInterval(pollTimers[key])
    delete pollTimers[key]
    const idx = instances.value.findIndex(i => i.id === id)
    if (idx !== -1) instances.value[idx] = { ...instances.value[idx], ...inst }
    if (inst.status === 'error') toastStore.showToast('Erreur lors du provisionnement Mage', true)
  }
}

async function deleteInstance(instance) {
  if (!confirm(`Supprimer l'instance Mage « ${instance.name} » ?`)) return
  const res = await apiDeleteMage(instance.id)
  if (res && res.ok) {
    toastStore.showToast('Instance Mage supprimée')
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
