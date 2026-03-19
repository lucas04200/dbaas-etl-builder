<template>
  <div class="instance-card" :data-hasura-id="instance.id">
    <div class="instance-card-head">
      <div style="display:flex;align-items:center;gap:10px">
        <div class="instance-card-icon" style="background:#EBF9FC">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M10 3L3 8v9h5v-5h4v5h5V8L10 3z" stroke="#1EB4D4" stroke-width="1.4" stroke-linejoin="round" fill="none"/>
          </svg>
        </div>
        <div>
          <div class="instance-card-name">{{ instance.name }}</div>
          <div class="instance-card-meta">port {{ instance.host_port }}{{ instance.linked_pg_name ? ' · ' + instance.linked_pg_name : '' }}</div>
        </div>
      </div>
      <span :class="['badge', 'badge-' + instance.status]">{{ statusLabel(instance.status) }}</span>
    </div>
    <div class="instance-card-actions">
      <code style="font-size:12px;color:#6B7280;background:#F3F4F6;padding:4px 8px;border-radius:6px;flex:1">
        http://localhost:{{ instance.host_port }} (X-Hasura-Admin-Secret: &lt;secret&gt;)
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
