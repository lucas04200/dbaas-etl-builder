<template>
  <div>
    <div v-if="loading" class="loading">Chargement des données…</div>
    <div v-else-if="error" class="empty">Erreur lors du chargement des données</div>
    <div v-else-if="!columns.length" class="empty">Aucune donnée</div>
    <div v-else>
      <p style="font-size:12px;color:#9CA3AF;margin-bottom:10px">{{ rows.length }} ligne(s) affichée(s) · 50 max</p>
      <div class="data-grid">
        <table>
          <thead>
            <tr>
              <th v-for="col in columns" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in rows" :key="ri">
              <td v-for="(val, ci) in row" :key="ci">
                <span v-if="val === null || val === undefined" class="null-val">NULL</span>
                <span v-else-if="val === true" class="bool-true">true</span>
                <span v-else-if="val === false" class="bool-false">false</span>
                <span v-else-if="String(val).length > 100" :title="String(val)">{{ String(val).substring(0, 100) }}…</span>
                <span v-else>{{ val }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { apiGetTableSample } from '../../lib/api.js'

const props = defineProps({
  instanceId: Number,
  dbName: String,
  tableName: String,
})

const columns = ref([])
const rows = ref([])
const loading = ref(true)
const error = ref(false)

async function load() {
  loading.value = true
  error.value = false
  const res = await apiGetTableSample(props.instanceId, props.dbName, props.tableName)
  if (!res || !res.ok) {
    error.value = true
    loading.value = false
    return
  }
  const data = await res.json()
  columns.value = data.columns
  rows.value = data.rows
  loading.value = false
}

onMounted(load)
watch(() => [props.instanceId, props.dbName, props.tableName], load)
</script>
