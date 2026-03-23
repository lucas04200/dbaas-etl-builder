<template>
  <div class="page-head">
    <div class="page-head-text">
      <h2>Architecture & Data Lineage</h2>
      <p>Visualisez la topologie réseau de vos bases de données, pipelines ETL et outils d'analytique interconnectés.</p>
    </div>
  </div>

  <div class="flow-container" v-if="!loading && nodes.length > 0">
    <VueFlow
      :nodes="nodes"
      :edges="edges"
      :default-viewport="{ zoom: 1 }"
      :min-zoom="0.2"
      :max-zoom="4"
      fit-view-on-init
    >
      <Background pattern-color="#aaa" />
      <Controls />
      <template #node-custom="props">
        <div 
          class="custom-node" 
          :style="{ borderColor: props.data.color, boxShadow: `0 4px 6px ${props.data.color}33` }"
        >
          <div class="node-header" :style="{ background: props.data.color }">
            {{ props.data.type.toUpperCase() }}
          </div>
          <div class="node-body">
            <strong>{{ props.data.label }}</strong>
            <div class="node-port" v-if="props.data.port">Port: {{ props.data.port }}</div>
          </div>
        </div>
      </template>
    </VueFlow>
  </div>
  
  <div class="empty" v-else-if="!loading" style="padding: 40px 0; text-align: center;">
    Aucun service déployé sur la plateforme.
  </div>
  <div class="loading" v-else>Chargement du graphe réseau...</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import { useAuthStore } from '../stores/auth.js'

const authStore = useAuthStore()
const nodes = ref([])
const edges = ref([])
const loading = ref(true)

async function loadGraph() {
  try {
    const res = await fetch('/api/architecture', {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    if (res.ok) {
      const data = await res.json()
      nodes.value = data.nodes
      edges.value = data.edges
    }
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadGraph()
})
</script>

<style scoped>
.flow-container {
  height: 600px;
  background: white;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  overflow: hidden;
  margin-top: 20px;
}

.custom-node {
  background: white;
  border: 2px solid #ccc;
  border-radius: 8px;
  overflow: hidden;
  width: 180px;
  transition: transform 0.2s;
}
.custom-node:hover {
  transform: translateY(-2px);
}
.node-header {
  color: white;
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-align: center;
}
.node-body {
  padding: 12px;
  text-align: center;
}
.node-body strong {
  display: block;
  font-size: 14px;
  color: #111827;
  margin-bottom: 4px;
}
.node-port {
  font-size: 11px;
  color: #6B7280;
}
</style>
