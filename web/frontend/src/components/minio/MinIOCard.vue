<template>
  <div class="instance-card" :data-minio-id="instance.id">
    <div class="instance-card-head">
      <div style="display:flex;align-items:center;gap:10px">
        <div class="instance-card-icon" style="background:#FFF1F2">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M4 14h12v2a1 1 0 01-1 1H5a1 1 0 01-1-1v-2z" stroke="#E11D48" stroke-width="1.4" stroke-linejoin="round"/>
            <path d="M4 10h12v4H4v-4z" stroke="#E11D48" stroke-width="1.4" stroke-linejoin="round"/>
            <path d="M6 6h8l2 4H4l2-4z" stroke="#E11D48" stroke-width="1.4" stroke-linejoin="round"/>
          </svg>
        </div>
        <div>
          <div class="instance-card-name">{{ instance.name }}</div>
          <div class="instance-card-meta">API :{{ instance.host_port }} · Console :{{ instance.console_port }}</div>
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
        API ↗
      </a>
      <a
        class="btn btn-secondary btn-sm"
        :href="`http://localhost:${instance.console_port}`"
        target="_blank"
        :style="instance.status !== 'running' ? 'pointer-events:none;opacity:.5' : ''"
      >
        Console ↗
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
