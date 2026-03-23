<template>
  <div class="instance-card" :data-postgrest-id="instance.id">
    <div class="instance-card-head">
      <div style="display:flex;align-items:center;gap:10px">
        <div class="instance-card-icon" style="background:#F0FDF4">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M6 5L2 10l4 5" stroke="#16A34A" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M14 5l4 5-4 5" stroke="#16A34A" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M12 4l-4 12" stroke="#16A34A" stroke-width="1.4" stroke-linecap="round"/>
          </svg>
        </div>
        <div>
          <div class="instance-card-name">{{ instance.name }}</div>
          <div class="instance-card-meta">port {{ instance.host_port }}{{ instance.linked_pg_name ? ` · DB: ${instance.linked_pg_name}` : '' }}</div>
        </div>
      </div>
      <span :class="['badge', 'badge-' + instance.status]">{{ statusLabel(instance.status) }}</span>
    </div>
    <div class="instance-card-actions">
      <a
        class="btn btn-primary btn-sm"
        :href="`http://localhost:${instance.host_port}`"
        target="_blank"
        :style="instance.status !== 'running' ? 'pointer-events:none;opacity:.5' : ''"
      >
        Ouvrir API ↗
      </a>
      <button v-if="isAdmin" class="btn btn-ghost btn-sm" @click="$emit('delete', instance)">Supprimer</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth.js'

defineProps({ instance: Object })
defineEmits(['delete'])

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.currentUser?.role === 'admin')

function statusLabel(s) {
  return { running: 'Actif', provisioning: 'Déploiement…', error: 'Erreur', stopped: 'Arrêté' }[s] || s
}
</script>
