<template>
  <div class="instance-card" :data-metabase-id="instance.id">
    <div class="instance-card-head">
      <div style="display:flex;align-items:center;gap:10px">
        <div class="instance-card-icon" style="background:#EFF6FF">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <rect x="2" y="13" width="3" height="5" rx="1" stroke="#3B82F6" stroke-width="1.4"/>
            <rect x="8.5" y="8" width="3" height="10" rx="1" stroke="#3B82F6" stroke-width="1.4"/>
            <rect x="15" y="4" width="3" height="14" rx="1" stroke="#3B82F6" stroke-width="1.4"/>
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
        Ouvrir Metabase ↗
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
