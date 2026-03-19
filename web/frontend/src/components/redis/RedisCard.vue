<template>
  <div class="instance-card" :data-redis-id="instance.id">
    <div class="instance-card-head">
      <div style="display:flex;align-items:center;gap:10px">
        <div class="instance-card-icon" style="background:#FFF7ED">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M3 6h14" stroke="#EA580C" stroke-width="1.4" stroke-linecap="round"/>
            <path d="M3 10h14" stroke="#EA580C" stroke-width="1.4" stroke-linecap="round"/>
            <path d="M3 14h14" stroke="#EA580C" stroke-width="1.4" stroke-linecap="round"/>
          </svg>
        </div>
        <div>
          <div class="instance-card-name">{{ instance.name }}</div>
          <div class="instance-card-meta">port {{ instance.host_port }}</div>
        </div>
      </div>
      <span :class="['badge', 'badge-' + instance.status]">{{ statusLabel(instance.status) }}</span>
    </div>
    <div class="instance-card-actions">
      <code style="font-size:12px;color:#6B7280;background:#F3F4F6;padding:4px 8px;border-radius:6px;flex:1">
        redis://localhost:{{ instance.host_port }}
      </code>
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
