<template>
  <div class="instance-card" :data-n8n-id="instance.id">
    <div class="instance-card-head">
      <div style="display:flex;align-items:center;gap:10px">
        <div class="instance-card-icon icon-n8n">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="3.5" cy="10" r="2" stroke="#EA580C" stroke-width="1.4"/>
            <circle cx="10" cy="3.5" r="2" stroke="#EA580C" stroke-width="1.4"/>
            <circle cx="16.5" cy="10" r="2" stroke="#EA580C" stroke-width="1.4"/>
            <circle cx="10" cy="16.5" r="2" stroke="#EA580C" stroke-width="1.4"/>
            <path d="M5.5 10h3M11.5 10h3M10 5.5v3M10 11.5v3" stroke="#EA580C" stroke-width="1.4" stroke-linecap="round"/>
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
        Ouvrir n8n ↗
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
