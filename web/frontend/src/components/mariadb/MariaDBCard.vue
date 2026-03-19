<template>
  <div class="instance-card" :data-mariadb-id="instance.id">
    <div class="instance-card-head">
      <div style="display:flex;align-items:center;gap:10px">
        <div class="instance-card-icon" style="background:#FDF4F0">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <ellipse cx="10" cy="6" rx="7" ry="3" stroke="#C0765A" stroke-width="1.4"/>
            <path d="M3 6v8c0 1.657 3.134 3 7 3s7-1.343 7-3V6" stroke="#C0765A" stroke-width="1.4"/>
            <path d="M3 10c0 1.657 3.134 3 7 3s7-1.343 7-3" stroke="#C0765A" stroke-width="1.4"/>
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
        mysql://root:&lt;pass&gt;@localhost:{{ instance.host_port }}/{{ instance.db_name || instance.name }}
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
