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
        :href="`http://${hostname}:${instance.host_port}`"
        target="_blank"
        :style="instance.status !== 'running' ? 'pointer-events:none;opacity:.5' : ''"
      >
        Ouvrir Metabase ↗
      </a>
      <button v-if="isAdmin" class="btn btn-ghost btn-sm" @click="$emit('delete', instance)">Supprimer</button>
    </div>

    <!-- Data Lineage / Connections -->
    <div class="instance-card-connections">
      <div class="connections-header">
        <span>Lineage des Données</span>
        <button v-if="isAdmin" class="btn-icon-sm" @click="toggleConnect" title="Connecter une base">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="8" y1="3" x2="8" y2="13"/><line x1="3" y1="8" x2="13" y2="8"/>
          </svg>
        </button>
      </div>
      
      <div v-if="loadingConns" class="connections-loading">Chargement…</div>
      <div v-else-if="!connections.length" class="connections-empty">Aucune base connectée</div>
      <div v-else class="connections-list">
        <div v-for="conn in connections" :key="conn.id" class="connection-tag" :title="conn.type === 'internal' ? 'Base de métadonnées interne' : 'Source de données externe'">
          <svg width="10" height="10" viewBox="0 0 16 16" :fill="conn.type === 'internal' ? '#888' : '#336791'"><circle cx="8" cy="8" r="8"/></svg>
          {{ conn.name }} <span v-if="conn.type === 'internal'" class="conn-type-hint">(interne)</span>
          <button v-if="isAdmin && conn.type !== 'internal'" class="btn-conn-del" @click="removeConn(conn.id)" title="Supprimer la connexion">×</button>
        </div>
      </div>

      <!-- Quick Add PG -->
      <div v-if="showConnect" class="conn-add-popover">
        <select v-model="selectedPg" class="form-select sm">
          <option value="" disabled>Choisir une base PG...</option>
          <option v-for="pg in availablePg" :key="pg.id" :value="pg.id">{{ pg.name }}</option>
        </select>
        <button class="btn btn-primary btn-sm" :disabled="!selectedPg" @click="addConn">Lier</button>
      </div>
    </div>
  </div>
</template>

<script setup>
const hostname = window.location.hostname;
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import { useToastStore } from '../../stores/toast.js'
import { apiGetServiceConnections, apiAddServiceConnection, apiDeleteServiceConnection, apiGetPostgres } from '../../lib/api.js'

const props = defineProps({ instance: Object })
defineEmits(['delete'])

const authStore = useAuthStore()
const toastStore = useToastStore()
const isAdmin = computed(() => authStore.currentUser?.role === 'admin')

const connections = ref([])
const availablePg = ref([])
const loadingConns = ref(false)
const showConnect = ref(false)
const selectedPg = ref('')

function statusLabel(s) {
  return { running: 'Actif', provisioning: 'Déploiement…', error: 'Erreur', stopped: 'Arrêté' }[s] || s
}

async function loadConnections() {
  loadingConns.value = true
  try {
    const res = await apiGetServiceConnections('metabase', props.instance.id)
    if (res && res.ok) connections.value = await res.json()
  } catch (err) { console.error(err) }
  finally { loadingConns.value = false }
}

async function toggleConnect() {
  showConnect.value = !showConnect.value
  if (showConnect.value && !availablePg.value.length) {
    const res = await apiGetPostgres()
    if (res && res.ok) {
      const allPg = await res.json()
      availablePg.value = allPg
    }
  }
}

async function addConn() {
  if (!selectedPg.value) return
  try {
    const res = await apiAddServiceConnection('metabase', props.instance.id, selectedPg.value)
    if (res && res.ok) {
      await loadConnections()
      showConnect.value = false
      selectedPg.value = ''
      toastStore.showToast('Base connectée avec succès')
    } else {
      const data = await res?.json().catch(() => ({}))
      toastStore.showToast(data.detail || 'Erreur lors de la connexion', true)
    }
  } catch (err) {
    console.error(err)
    toastStore.showToast('Erreur serveur lors de la connexion', true)
  }
}

async function removeConn(pgId) {
  try {
    const res = await apiDeleteServiceConnection('metabase', props.instance.id, pgId)
    if (res && res.ok) {
      await loadConnections()
      toastStore.showToast('Base déconnectée')
    }
  } catch (err) { console.error(err) }
}

onMounted(loadConnections)
</script>

<style scoped>
.instance-card-connections {
  margin-top: 15px;
  padding-top: 12px;
  border-top: 1px dashed #e5e7eb;
}
.connections-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.connections-header span {
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
}
.btn-icon-sm {
  background: none;
  border: none;
  color: #3B82F6;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}
.btn-icon-sm:hover { background: #eff6ff; }

.connections-loading, .connections-empty {
  font-size: 12px;
  color: #9CA3AF;
  font-style: italic;
  padding: 4px 0;
}
.connections-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.connection-tag {
  background: #f3f4f6;
  border-radius: 12px;
  padding: 3px 8px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #374151;
}
.conn-type-hint {
  font-size: 10px;
  opacity: 0.6;
  font-style: italic;
  margin-left: -2px;
}
.btn-conn-del {
  background: none;
  border: none;
  color: #9CA3AF;
  font-weight: bold;
  cursor: pointer;
  padding: 0 2px;
}
.btn-conn-del:hover { color: #ef4444; }

.conn-add-popover {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  animation: slideIn 0.2s ease-out;
}
.form-select.sm {
  flex: 1;
  font-size: 12px;
  padding: 4px 8px;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
