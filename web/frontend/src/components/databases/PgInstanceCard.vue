<template>
  <div class="instance-card" :data-pg-id="instance.id">
    <div class="instance-card-head">
      <div style="display:flex;align-items:center;gap:10px">
        <div class="instance-card-icon icon-pg">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <ellipse cx="10" cy="5" rx="6" ry="2.2" stroke="#4C6EF5" stroke-width="1.4"/>
            <path d="M4 5v5c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2V5" stroke="#4C6EF5" stroke-width="1.4"/>
            <path d="M4 10v5c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2v-5" stroke="#4C6EF5" stroke-width="1.4"/>
          </svg>
        </div>
        <div>
          <div class="instance-card-name">{{ instance.name }}</div>
          <div class="instance-card-meta">port {{ instance.host_port }} · {{ instance.db_name }}</div>
        </div>
      </div>
      <span :class="['badge', 'badge-' + instance.status]">{{ statusLabel(instance.status) }}</span>
    </div>
    <div class="instance-card-actions">
      <router-link to="/catalog" class="btn btn-secondary btn-sm" title="Explorer dans le Catalog">
        Catalog →
      </router-link>
      <button v-if="isAdmin" class="btn btn-ghost btn-sm" @click="$emit('delete', instance)">Supprimer</button>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '../../stores/auth.js'
import { computed } from 'vue'

const props = defineProps({
  instance: Object,
})
defineEmits(['delete'])

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.currentUser?.role === 'admin')

function statusLabel(s) {
  return { running: 'Actif', provisioning: 'Déploiement…', error: 'Erreur', stopped: 'Arrêté' }[s] || s
}
</script>
