<template>
  <div class="page-head">
    <div class="page-head-text">
      <h2>Monitoring</h2>
      <p>CPU / RAM / IO en temps réel · statuts synchronisés avec Docker</p>
    </div>
    <div style="display:flex;gap:8px">
      <button class="btn btn-secondary" :disabled="syncing" @click="syncStatuses">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none" :class="{ spin: syncing }">
          <path d="M10.5 6a4.5 4.5 0 1 1-1.2-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          <path d="M10.5 2v3h-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Synchroniser statuts
      </button>
      <button class="btn btn-secondary" @click="fetchStats">
        Actualiser stats
      </button>
    </div>
  </div>

  <!-- Sync result -->
  <div v-if="syncResult" class="sync-banner" :class="syncResult.synced ? 'sync-changed' : 'sync-ok'">
    <template v-if="syncResult.synced">
      {{ syncResult.synced }} statut(s) corrigé(s) :
      <span v-for="c in syncResult.changes" :key="c.container" class="sync-item">
        {{ c.name }} <span class="sync-old">{{ c.old }}</span> → <span class="sync-new">{{ c.new }}</span>
      </span>
    </template>
    <template v-else>Tous les statuts sont à jour.</template>
  </div>

  <div v-if="error" class="error-box">
    <strong>Erreur :</strong> {{ error }}
  </div>

  <div class="stats-grid" v-else-if="stats.length">
    <div v-for="c in stats" :key="c.id" class="stat-card">
      <div class="stat-header">
        <span class="stat-name">{{ c.name }}</span>
        <div style="display:flex;gap:6px;align-items:center">
          <button class="logs-btn" @click="openLogs(c.name)" title="Voir les logs">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <rect x="1" y="1.5" width="10" height="9" rx="1" stroke="currentColor" stroke-width="1.2"/>
              <path d="M3 4h6M3 6h4M3 8h5" stroke="currentColor" stroke-width="1.1" stroke-linecap="round"/>
            </svg>
            Logs
          </button>
          <span class="badge" :class="getBadgeState(c.cpu, c.mem_perc)">Actif</span>
        </div>
      </div>

      <div class="stat-row">
        <span>CPU</span>
        <strong :style="getCpuStyle(c.cpu)">{{ c.cpu }}</strong>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" :style="getFill(c.cpu)"></div>
      </div>

      <div class="stat-row">
        <span>RAM</span>
        <strong :style="getMemStyle(c.mem_perc)">{{ c.mem }} ({{ c.mem_perc }})</strong>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" :style="getFill(c.mem_perc)"></div>
      </div>

      <div class="stat-row io-row">
        <small>NET : {{ c.net }}</small>
        <small>I/O : {{ c.block }}</small>
      </div>
    </div>
  </div>

  <div v-else-if="!loading" class="empty" style="padding:40px 0;text-align:center">
    Aucun container en cours d'exécution.
  </div>
  <div class="loading" v-else>Connexion au démon Docker…</div>

  <LogsModal
    v-if="logsContainer"
    :container-name="logsContainer"
    @close="logsContainer = null"
  />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { apiSyncStatuses } from '../lib/api.js'
import { useToastStore } from '../stores/toast.js'
import LogsModal from '../components/shared/LogsModal.vue'

const toastStore = useToastStore()
const stats = ref([])
const loading = ref(true)
const error = ref(null)
const syncing = ref(false)
const syncResult = ref(null)
const logsContainer = ref(null)
let interval = null

async function fetchStats() {
  loading.value = true
  try {
    const res = await fetch('/api/monitoring')
    if (!res.ok) throw new Error("Erreur API monitoring")
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    stats.value = data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function syncStatuses() {
  syncing.value = true
  syncResult.value = null
  const res = await apiSyncStatuses()
  syncing.value = false
  if (!res || !res.ok) {
    toastStore.showToast('Erreur lors de la synchronisation', true)
    return
  }
  syncResult.value = await res.json()
  setTimeout(() => { syncResult.value = null }, 6000)
}

function openLogs(name) {
  logsContainer.value = name
}

function parsePerc(percStr) {
  return parseFloat((percStr || '0').replace('%', '')) || 0
}
function getFill(percStr) {
  const v = Math.min(parsePerc(percStr), 100)
  return `width:${v}%;background:${v > 85 ? '#EF4444' : v > 60 ? '#F59E0B' : '#10B981'}`
}
function getBadgeState(cpu, mem) {
  return (parsePerc(cpu) > 90 || parsePerc(mem) > 90) ? 'badge-error' : 'badge-running'
}
function getCpuStyle(cpu) {
  const v = parsePerc(cpu)
  return v > 90 ? { color: '#EF4444' } : v > 60 ? { color: '#F59E0B' } : {}
}
function getMemStyle(mem) {
  const v = parsePerc(mem)
  return v > 90 ? { color: '#EF4444' } : v > 60 ? { color: '#F59E0B' } : {}
}

onMounted(() => { fetchStats(); interval = setInterval(fetchStats, 8000) })
onUnmounted(() => { if (interval) clearInterval(interval) })
</script>

<style scoped>
.error-box { background:#FEF2F2;color:#991B1B;padding:16px;border-radius:8px;margin-top:20px; }

.sync-banner {
  margin-top: 12px; padding: 10px 14px; border-radius: 8px;
  font-size: 13px; display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
}
.sync-ok { background: #F0FDF4; color: #15803D; border: 1px solid #86EFAC; }
.sync-changed { background: #FFF7ED; color: #C2410C; border: 1px solid #FED7AA; }
.sync-item { display: inline-flex; align-items: center; gap: 4px; background: white; padding: 1px 7px; border-radius: 6px; }
.sync-old { color: #9CA3AF; text-decoration: line-through; }
.sync-new { font-weight: 600; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px; margin-top: 20px;
}
.stat-card {
  background: var(--white); border-radius: 10px;
  border: 1px solid var(--border); padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.stat-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;
}
.stat-name { font-weight: 600; font-size: 13.5px; color: var(--text-primary); }

.logs-btn {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; font-family: inherit;
  padding: 3px 8px; border-radius: 6px;
  border: 1px solid var(--border); background: var(--content-bg);
  color: var(--text-muted); cursor: pointer;
}
.logs-btn:hover { color: var(--accent); border-color: var(--accent); }

.stat-row {
  display: flex; justify-content: space-between;
  font-size: 13px; color: var(--text-secondary);
  margin-bottom: 5px; margin-top: 10px;
}
.io-row { margin-top: 14px; color: #9CA3AF; font-family: monospace; font-size: 11.5px; }
.progress-bar-bg { width:100%;height:5px;background:#F3F4F6;border-radius:3px;overflow:hidden; }
.progress-bar-fill { height:100%;transition:width 0.5s,background 0.5s; }

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
