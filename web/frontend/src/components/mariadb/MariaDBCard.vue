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
        mysql://root:&lt;pass&gt;@{{ hostname }}:{{ instance.host_port }}/{{ instance.db_name || instance.name }}
      </code>
      <button class="btn btn-primary btn-sm" @click="downloadBackup" :disabled="instance.status !== 'running'" title="Télécharger un Dump SQL">
        Backup ⬇
      </button>
      <button v-if="isAdmin" class="btn btn-ghost btn-sm" @click="$emit('delete', instance)">Supprimer</button>
    </div>
  </div>
</template>

<script setup>
const hostname = window.location.hostname;
import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth.js'

const props = defineProps({ instance: Object })
defineEmits(['delete'])

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.currentUser?.role === 'admin')

function statusLabel(s) {
  return { running: 'Actif', provisioning: 'Déploiement…', error: 'Erreur', stopped: 'Arrêté' }[s] || s
}

import { useToastStore } from '../../stores/toast.js'
const toastStore = useToastStore()

async function downloadBackup() {
  if (props.instance.status !== 'running') return
  const toastId = toastStore.showToast("Génération du backup en cours...", false)
  try {
    const res = await fetch(`/api/mariadb/${props.instance.id}/backup`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    if (!res.ok) {
      toastStore.showToast("Erreur lors du backup", true)
      return
    }
    const filenameMatch = res.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/)
    const filename = filenameMatch ? filenameMatch[1] : 'backup.sql'
    
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
    
    toastStore.showToast("Backup téléchargé avec succès !")
  } catch (err) {
    toastStore.showToast("Erreur lors du téléchargement", true)
  }
}
</script>
