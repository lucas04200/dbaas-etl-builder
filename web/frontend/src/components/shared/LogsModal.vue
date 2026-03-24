<template>
  <div class="logs-overlay" @click.self="$emit('close')">
    <div class="logs-panel">
      <div class="logs-header">
        <div>
          <div class="logs-title">Logs — <span class="logs-container">{{ containerName }}</span></div>
          <div class="logs-sub">{{ lines.length }} lignes · <span class="logs-tail">{{ tail }} dernières</span></div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <select class="tail-select" v-model.number="tail" @change="loadLogs">
            <option :value="100">100 lignes</option>
            <option :value="200">200 lignes</option>
            <option :value="500">500 lignes</option>
            <option :value="1000">1000 lignes</option>
          </select>
          <button class="logs-refresh" @click="loadLogs" :disabled="loading" title="Actualiser">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" :class="{ spin: loading }">
              <path d="M10.5 6a4.5 4.5 0 1 1-1.2-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              <path d="M10.5 2v3h-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <button class="logs-close" @click="$emit('close')">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="logs-body" ref="logsEl">
        <div v-if="loading && !lines.length" class="logs-loading">Chargement…</div>
        <div v-else-if="error" class="logs-error">{{ error }}</div>
        <div v-else-if="!lines.length" class="logs-empty">Aucun log disponible.</div>
        <div v-else class="logs-content">
          <div
            v-for="(line, i) in lines"
            :key="i"
            class="log-line"
            :class="lineClass(line)"
          >{{ line }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { apiGetContainerLogs } from '../../lib/api.js'

const props = defineProps({
  containerName: { type: String, required: true },
})
defineEmits(['close'])

const lines = ref([])
const loading = ref(false)
const error = ref(null)
const tail = ref(200)
const logsEl = ref(null)

function lineClass(line) {
  const l = line.toLowerCase()
  if (l.includes('error') || l.includes('fatal') || l.includes('critical')) return 'log-error'
  if (l.includes('warn')) return 'log-warn'
  return ''
}

async function loadLogs() {
  loading.value = true
  error.value = null
  const res = await apiGetContainerLogs(props.containerName, tail.value)
  if (!res || !res.ok) {
    error.value = 'Impossible de récupérer les logs.'
    loading.value = false
    return
  }
  const data = await res.json()
  lines.value = data.lines || []
  loading.value = false
  await nextTick()
  if (logsEl.value) logsEl.value.scrollTop = logsEl.value.scrollHeight
}

onMounted(loadLogs)
</script>

<style scoped>
.logs-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
}
.logs-panel {
  background: #0F172A;
  border-radius: 12px;
  width: 820px; max-width: 96vw;
  height: 580px; max-height: 90vh;
  display: flex; flex-direction: column;
  box-shadow: 0 24px 64px rgba(0,0,0,0.4);
  overflow: hidden;
}
.logs-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-bottom: 1px solid #1E293B; flex-shrink: 0;
}
.logs-title { font-size: 14px; font-weight: 600; color: #F1F5F9; }
.logs-container { color: #60A5FA; }
.logs-sub { font-size: 11px; color: #64748B; margin-top: 2px; }
.logs-tail { color: #94A3B8; }

.tail-select {
  background: #1E293B; border: 1px solid #334155; color: #94A3B8;
  border-radius: 6px; padding: 4px 8px; font-size: 12px; font-family: inherit; cursor: pointer;
}
.logs-refresh, .logs-close {
  background: none; border: none; cursor: pointer; color: #64748B;
  padding: 4px; border-radius: 6px; display: flex; align-items: center;
}
.logs-refresh:hover, .logs-close:hover { color: #F1F5F9; background: #1E293B; }

.logs-body {
  flex: 1; overflow-y: auto; padding: 12px 0;
  font-family: 'SF Mono', 'Fira Mono', 'Consolas', monospace;
  font-size: 12px; line-height: 1.6;
}
.logs-loading, .logs-empty { color: #64748B; padding: 20px 18px; }
.logs-error { color: #F87171; padding: 20px 18px; }

.log-line {
  padding: 1px 18px;
  color: #CBD5E1;
  white-space: pre-wrap;
  word-break: break-all;
}
.log-line:hover { background: #1E293B; }
.log-line.log-error { color: #F87171; }
.log-line.log-warn { color: #FBD15B; }

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Scrollbar style pour la zone dark */
.logs-body::-webkit-scrollbar { width: 6px; }
.logs-body::-webkit-scrollbar-track { background: transparent; }
.logs-body::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
</style>
