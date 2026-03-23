<template>
  <div class="page-head">
    <div class="page-head-text">
      <h2>Monitoring Temps Réel</h2>
      <p>Consommation électrique et santé des conteneurs isolés (Live CPU/RAM/IO).</p>
    </div>
    <button class="btn btn-secondary" @click="fetchStats">
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" :class="{ 'spin': loading }">
        <path d="M10.5 6a4.5 4.5 0 1 1-1.2-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
        <path d="M10.5 2v3h-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      Actualiser
    </button>
  </div>

  <div v-if="error" class="error-box">
    <strong>Erreur:</strong> {{ error }}
  </div>

  <div class="stats-grid" v-else-if="stats.length">
    <div v-for="c in stats" :key="c.id" class="stat-card">
      <div class="stat-header">
        <span class="stat-name">{{ c.name }}</span>
        <span class="badge" :class="getBadgeState(c.cpu, c.mem_perc)">En Ligne</span>
      </div>
      
      <div class="stat-row">
        <span>CPU :</span>
        <strong :style="getCpuStyle(c.cpu)">{{ c.cpu }}</strong>
      </div>
      <div class="progress-bar-bg"><div class="progress-bar-fill" :style="getFill(c.cpu)"></div></div>

      <div class="stat-row">
        <span>RAM :</span>
        <strong :style="getMemStyle(c.mem_perc)">{{ c.mem }} ({{ c.mem_perc }})</strong>
      </div>
      <div class="progress-bar-bg"><div class="progress-bar-fill" :style="getFill(c.mem_perc)"></div></div>

      <div class="stat-row io-row">
        <small>NET : {{ c.net }}</small>
        <small>I/O : {{ c.block }}</small>
      </div>
    </div>
  </div>
  
  <div v-else-if="!loading" class="empty" style="padding: 40px 0; text-align: center;">
    Aucun conteneur n'est actuellement en cours d'exécution.
  </div>
  <div class="loading" v-else>Connexion au démon Docker...</div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth.js'

const authStore = useAuthStore()
const stats = ref([])
const loading = ref(true)
const error = ref(null)
let interval = null

async function fetchStats() {
  loading.value = true
  try {
    const res = await fetch('/api/monitoring', {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    if (!res.ok) {
      throw new Error("Droits insuffisants ou erreur de l'API Docker.")
    }
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    stats.value = data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function parsePerc(percStr) {
  return parseFloat(percStr.replace('%', '')) || 0
}

function getFill(percStr) {
  const v = Math.min(parsePerc(percStr), 100)
  return `width: ${v}%; background-color: ${v > 85 ? '#EF4444' : v > 60 ? '#F59E0B' : '#10B981'};`
}

function getBadgeState(cpu, mem) {
  if (parsePerc(cpu) > 90 || parsePerc(mem) > 90) return 'badge-error'
  return 'badge-running'
}

function getCpuStyle(cpu) {
  const v = parsePerc(cpu)
  return v > 90 ? { color: '#EF4444' } : v > 60 ? { color: '#F59E0B' } : {}
}

function getMemStyle(mem) {
  const v = parsePerc(mem)
  return v > 90 ? { color: '#EF4444' } : v > 60 ? { color: '#F59E0B' } : {}
}

onMounted(() => {
  fetchStats()
  interval = setInterval(fetchStats, 5000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<style scoped>
.error-box {
  background: #FEF2F2; color: #991B1B; padding: 16px; border-radius: 8px; margin-top: 20px;
}
.spin { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  margin-top: 20px;
}
.stat-card {
  background: white;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.stat-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
}
.stat-name { font-weight: 600; font-size: 14px; color: #111827; }
.stat-row {
  display: flex; justify-content: space-between; font-size: 13px; color: #4B5563; margin-bottom: 6px; margin-top: 12px;
}
.io-row { margin-top: 16px; color: #9CA3AF; font-family: monospace; }
.progress-bar-bg {
  width: 100%; height: 6px; background: #F3F4F6; border-radius: 3px; overflow: hidden;
}
.progress-bar-fill {
  height: 100%; transition: width 0.5s ease-in-out, background-color 0.5s;
}
</style>
