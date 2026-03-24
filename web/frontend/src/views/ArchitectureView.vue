<template>
  <div class="page-head">
    <div class="page-head-text">
      <h2>Architecture</h2>
      <p>Topologie de vos services et leurs connexions. Déplacez les nœuds pour réorganiser.</p>
    </div>
    <div style="display:flex;gap:8px">
      <button class="btn btn-secondary" @click="resetLayout" title="Réinitialiser les positions">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
          <path d="M10.5 6a4.5 4.5 0 1 1-1.2-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          <path d="M10.5 2v3h-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Réinitialiser
      </button>
      <span v-if="saving" class="save-indicator">Sauvegarde…</span>
      <span v-else-if="saved" class="save-indicator saved">Positions sauvegardées ✓</span>
    </div>
  </div>

  <div v-if="connectHint" class="connect-hint">
    Glissez depuis le <strong>●</strong> d'un nœud vers un autre pour créer un lien · Cliquez sur un lien puis <kbd>Suppr</kbd> pour le supprimer
  </div>

  <div class="flow-container" v-if="!loading && nodes.length > 0">
    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      :default-viewport="{ zoom: 0.9, x: 0, y: 0 }"
      :min-zoom="0.2"
      :max-zoom="4"
      fit-view-on-init
      @node-drag-stop="onNodeDragStop"
      @connect="onConnect"
      @edge-click="onEdgeClick"
      @edges-change="onEdgesChange"
    >
      <Background pattern-color="#E5E7EB" :gap="20" />
      <Controls />
      <MiniMap />

      <template #node-custom="props">
        <div
          class="custom-node"
          :class="'status-' + props.data.status"
          :style="{ borderColor: props.data.color }"
        >
          <div class="node-header" :style="{ background: props.data.color }">
            <span class="node-type">{{ props.data.type }}</span>
            <span class="node-status-dot" :class="'dot-' + props.data.status"></span>
          </div>
          <div class="node-body">
            <strong>{{ props.data.label }}</strong>
            <div class="node-port" v-if="props.data.port">:{{ props.data.port }}</div>
            <div class="node-internal-pg" v-if="props.data.hasInternalPg">
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                <ellipse cx="5" cy="2.5" rx="3.5" ry="1.2" stroke="currentColor" stroke-width="0.9"/>
                <path d="M1.5 2.5v2c0 .7 1.6 1.2 3.5 1.2s3.5-.5 3.5-1.2v-2" stroke="currentColor" stroke-width="0.9"/>
                <path d="M1.5 4.5v2c0 .7 1.6 1.2 3.5 1.2s3.5-.5 3.5-1.2v-2" stroke="currentColor" stroke-width="0.9"/>
              </svg>
              DB interne
            </div>
          </div>
          <!-- Handles for connections -->
          <Handle type="source" :position="Position.Right" />
          <Handle type="target" :position="Position.Left" />
        </div>
      </template>
    </VueFlow>
  </div>

  <div v-else-if="!loading" class="empty" style="padding:60px 0;text-align:center;color:#9CA3AF">
    Aucun service déployé. Créez des instances depuis la bibliothèque.
  </div>
  <div v-else class="loading" style="padding:40px 0;text-align:center;color:#9CA3AF">
    Chargement du graphe…
  </div>

  <EdgeLabelModal
    v-if="pendingConnection"
    :source="pendingConnection.source"
    :target="pendingConnection.target"
    @confirm="finishConnect"
    @cancel="pendingConnection = null"
  />

  <EdgeEditModal
    v-if="editingEdge"
    :source="editingEdge.source"
    :target="editingEdge.target"
    :current-label="editingEdge.label || ''"
    :is-manual="editingEdge.id?.startsWith('manual-')"
    @save="saveEdge"
    @delete="deleteEdge"
    @cancel="editingEdge = null"
  />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { VueFlow, useVueFlow, Position } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
import { Handle } from '@vue-flow/core'
import { fetchWithAuth } from '../lib/api.js'
import EdgeLabelModal from '../components/architecture/EdgeLabelModal.vue'
import EdgeEditModal from '../components/architecture/EdgeEditModal.vue'

const nodes = ref([])
const edges = ref([])
const loading = ref(true)
const saving = ref(false)
const saved = ref(false)
const connectHint = ref(false)
const pendingConnection = ref(null)
const editingEdge = ref(null)

async function loadGraph() {
  const res = await fetchWithAuth('/api/architecture')
  if (res && res.ok) {
    const data = await res.json()
    nodes.value = data.nodes
    edges.value = data.edges
  }
  loading.value = false
}

async function onNodeDragStop({ nodes: movedNodes }) {
  const positions = {}
  movedNodes.forEach(n => {
    positions[n.id] = { x: n.position.x, y: n.position.y }
  })
  saving.value = true
  saved.value = false
  await fetchWithAuth('/api/architecture/positions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ positions }),
  })
  saving.value = false
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}

function onConnect(params) {
  pendingConnection.value = params
}

async function finishConnect(label) {
  const params = pendingConnection.value
  pendingConnection.value = null
  const edgeId = `manual-${params.source}-${params.target}-${Date.now()}`
  const newEdge = {
    id: edgeId,
    source: params.source,
    target: params.target,
    label,
    animated: true,
    style: { stroke: '#6B7280', strokeWidth: 2, strokeDasharray: '6,3' },
    labelStyle: { fontSize: '10px', fill: '#6B7280' },
  }
  edges.value = [...edges.value, newEdge]
  await fetchWithAuth('/api/architecture/edges', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: edgeId, source: params.source, target: params.target, label }),
  })
}

function onEdgeClick({ edge }) {
  editingEdge.value = edge
}

async function saveEdge(label) {
  const edge = editingEdge.value
  editingEdge.value = null
  edges.value = edges.value.map(e => e.id === edge.id ? { ...e, label } : e)
  await fetchWithAuth(`/api/architecture/edges/${encodeURIComponent(edge.id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label }),
  })
}

async function deleteEdge() {
  const edge = editingEdge.value
  editingEdge.value = null
  edges.value = edges.value.filter(e => e.id !== edge.id)
  if (edge.id.startsWith('manual-')) {
    await fetchWithAuth(`/api/architecture/edges/${encodeURIComponent(edge.id)}`, { method: 'DELETE' })
  }
}

async function onEdgesChange(changes) {
  // Handle edge removals via keyboard (Delete key on selected edge)
  for (const change of changes) {
    if (change.type === 'remove' && change.id.startsWith('manual-')) {
      await fetchWithAuth(`/api/architecture/edges/${encodeURIComponent(change.id)}`, { method: 'DELETE' })
    }
  }
}

async function resetLayout() {
  if (!confirm('Réinitialiser toutes les positions au layout automatique ?')) return
  await fetchWithAuth('/api/architecture/positions', { method: 'DELETE' })
  loadGraph()
}

onMounted(() => {
  loadGraph()
  // Show hint for 5s on first visit
  connectHint.value = true
  setTimeout(() => { connectHint.value = false }, 6000)
})
</script>

<style scoped>
.flow-container {
  height: calc(100vh - 160px);
  min-height: 500px;
  background: #F9FAFB;
  border-radius: 12px;
  border: 1px solid var(--border);
  overflow: hidden;
  margin-top: 16px;
}

.connect-hint {
  margin-top: 10px;
  font-size: 12px;
  color: #6B7280;
  background: #F9FAFB;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 14px;
}
.connect-hint kbd {
  background: #E5E7EB; border-radius: 4px;
  padding: 1px 5px; font-size: 11px;
}

.save-indicator {
  font-size: 12px;
  color: var(--text-muted);
  align-self: center;
  padding: 0 4px;
}
.save-indicator.saved { color: #15803D; }

/* ── Node styles ── */
.custom-node {
  background: white;
  border: 2px solid #ccc;
  border-radius: 10px;
  overflow: hidden;
  width: 160px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  transition: box-shadow 0.15s;
  cursor: grab;
}
.custom-node:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.14);
}

.node-header {
  color: white;
  padding: 5px 10px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.node-type { flex: 1; }

.node-status-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: rgba(255,255,255,0.4);
  flex-shrink: 0;
}
.dot-running { background: #4ADE80; }
.dot-error   { background: #F87171; }
.dot-stopped { background: #9CA3AF; }
.dot-provisioning { background: #FCD34D; animation: pulse 1s infinite; }

.node-body {
  padding: 10px 12px;
  text-align: center;
}
.node-body strong {
  display: block;
  font-size: 13px;
  color: #111827;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.node-port {
  font-size: 11px;
  color: #9CA3AF;
  font-family: monospace;
}
.node-internal-pg {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-top: 5px;
  font-size: 10px;
  color: #6B7280;
  background: #F3F4F6;
  padding: 2px 6px;
  border-radius: 20px;
}

@keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:0.4 } }
</style>
