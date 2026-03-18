<template>
  <div>
    <div v-if="loading" class="loading">Chargement…</div>
    <div v-else>
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-card-label">Lignes</div>
          <div class="stat-card-value">{{ rowCount }}</div>
          <div class="stat-card-sub">estimation pg_class</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-label">Taille totale</div>
          <div class="stat-card-value">{{ stats.total_size || '—' }}</div>
          <div class="stat-card-sub">données + index</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-label">Taille table</div>
          <div class="stat-card-value">{{ stats.table_size || '—' }}</div>
          <div class="stat-card-sub">sans index</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-label">Index</div>
          <div class="stat-card-value">{{ stats.index_count ?? '—' }}</div>
          <div class="stat-card-sub">schéma public</div>
        </div>
      </div>
      <div class="card" style="margin-bottom:0">
        <div class="card-title" style="margin-bottom:12px">{{ cols.length }} colonnes</div>
        <table>
          <thead>
            <tr>
              <th>Nom</th>
              <th>Type</th>
              <th>Nullable</th>
              <th>Défaut</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in cols" :key="c.name">
              <td><strong style="font-family:'SF Mono','Monaco','Menlo',monospace;font-size:13px">{{ c.name }}</strong></td>
              <td><span class="col-type">{{ c.type }}</span></td>
              <td :class="c.nullable === 'YES' ? 'nullable-yes' : 'nullable-no'">{{ c.nullable === 'YES' ? 'oui' : 'non' }}</td>
              <td style="color:#9CA3AF;font-size:12px;font-family:monospace">{{ c.default_val ? String(c.default_val).substring(0, 40) : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { apiGetTableColumns, apiGetTableStats } from '../../lib/api.js'

const props = defineProps({
  instanceId: Number,
  dbName: String,
  tableName: String,
})

const cols = ref([])
const stats = ref({})
const loading = ref(true)

const rowCount = computed(() => {
  if (stats.value.row_count != null) {
    return Number(stats.value.row_count).toLocaleString('fr-FR') + ' ~'
  }
  return '—'
})

async function load() {
  loading.value = true
  const [colsRes, statsRes] = await Promise.all([
    apiGetTableColumns(props.instanceId, props.dbName, props.tableName),
    apiGetTableStats(props.instanceId, props.dbName, props.tableName),
  ])
  cols.value = colsRes && colsRes.ok ? await colsRes.json() : []
  stats.value = statsRes && statsRes.ok ? await statsRes.json() : {}
  loading.value = false
}

onMounted(load)
watch(() => [props.instanceId, props.dbName, props.tableName], load)
</script>
