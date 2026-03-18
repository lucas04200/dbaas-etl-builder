<template>
  <div class="catalog-tree">
    <div class="catalog-tree-head">Sources de données</div>
    <div class="catalog-tree-body">
      <div v-if="loadingInstances" style="padding:10px 14px;font-size:13px;color:#9CA3AF">Chargement…</div>
      <div v-else-if="!instances.length" class="tree-empty">
        Aucune instance active.<br>Déployez d'abord une base de données.
      </div>
      <div v-else>
        <div v-for="inst in instances" :key="inst.id" class="tree-node">
          <div class="tree-item" @click="toggleInstance(inst)">
            <svg
              :class="['tree-chevron', { open: openInstances[inst.id] }]"
              width="12" height="12" viewBox="0 0 12 12" fill="none"
            >
              <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style="flex-shrink:0">
              <ellipse cx="7" cy="3.2" rx="4.5" ry="1.6" stroke="#4C6EF5" stroke-width="1.2"/>
              <path d="M2.5 3.2v3.6c0 .9 2 1.6 4.5 1.6s4.5-.7 4.5-1.6V3.2" stroke="#4C6EF5" stroke-width="1.2"/>
              <path d="M2.5 6.8v3.6c0 .9 2 1.6 4.5 1.6s4.5-.7 4.5-1.6V6.8" stroke="#4C6EF5" stroke-width="1.2"/>
            </svg>
            <span class="tree-label" style="font-weight:600">{{ inst.name }}</span>
            <span class="tree-meta">:{{ inst.host_port }}</span>
          </div>
          <div v-if="openInstances[inst.id]" class="tree-children open">
            <div v-if="loadingDbs[inst.id]" class="tree-empty" style="padding-left:26px">Chargement…</div>
            <div v-else-if="dbs[inst.id] && !dbs[inst.id].length" class="tree-empty" style="padding-left:26px">Aucune base</div>
            <div v-else>
              <div v-for="db in (dbs[inst.id] || [])" :key="db.name" class="tree-node">
                <div class="tree-item tree-l1" @click="toggleDb(inst, db)">
                  <svg
                    :class="['tree-chevron', { open: openDbs[catId(inst.id, db.name)] }]"
                    width="11" height="11" viewBox="0 0 12 12" fill="none"
                  >
                    <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style="flex-shrink:0">
                    <circle cx="6.5" cy="6.5" r="5" stroke="#6B7280" stroke-width="1.2"/>
                    <path d="M6.5 1.5v11M1.5 6.5h10" stroke="#6B7280" stroke-width="1.2"/>
                  </svg>
                  <span class="tree-label">{{ db.name }}</span>
                  <span v-if="db.size" class="tree-meta">{{ db.size }}</span>
                </div>
                <div v-if="openDbs[catId(inst.id, db.name)]" class="tree-children open">
                  <div v-if="loadingTables[catId(inst.id, db.name)]" class="tree-empty" style="padding-left:40px">Chargement…</div>
                  <div v-else-if="tables[catId(inst.id, db.name)] && !tables[catId(inst.id, db.name)].length" class="tree-empty" style="padding-left:40px">Aucune table</div>
                  <div v-else>
                    <div
                      v-for="t in (tables[catId(inst.id, db.name)] || [])"
                      :key="t.name"
                      :class="['tree-item', 'tree-l2', { selected: isSelected(inst.id, db.name, t.name) }]"
                      @click="selectTable(inst, db, t)"
                    >
                      <svg v-if="t.type === 'VIEW'" width="12" height="12" viewBox="0 0 12 12" fill="none" style="flex-shrink:0">
                        <path d="M1 6s2-4 5-4 5 4 5 4-2 4-5 4-5-4-5-4z" stroke="#9CA3AF" stroke-width="1.2"/>
                        <circle cx="6" cy="6" r="1.5" stroke="#9CA3AF" stroke-width="1.2"/>
                      </svg>
                      <svg v-else width="12" height="12" viewBox="0 0 12 12" fill="none" style="flex-shrink:0">
                        <rect x="1" y="1" width="10" height="10" rx="1.5" stroke="#6B7280" stroke-width="1.2"/>
                        <line x1="1" y1="4.5" x2="11" y2="4.5" stroke="#6B7280" stroke-width="1.2"/>
                        <line x1="1" y1="7.5" x2="11" y2="7.5" stroke="#6B7280" stroke-width="1.2"/>
                        <line x1="4.5" y1="4.5" x2="4.5" y2="11" stroke="#6B7280" stroke-width="1.2"/>
                      </svg>
                      <span class="tree-label">{{ t.name }}</span>
                      <span class="tree-meta">{{ t.column_count }}c</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiGetPostgres, apiGetDatabases, apiGetTables } from '../../lib/api.js'

const emit = defineEmits(['select-table', 'clear-selection'])

const instances = ref([])
const loadingInstances = ref(true)
const openInstances = ref({})
const dbs = ref({})
const loadingDbs = ref({})
const openDbs = ref({})
const tables = ref({})
const loadingTables = ref({})
const selectedTable = ref(null)

function catId(...parts) {
  return parts.map(String).join('__').replace(/[^a-zA-Z0-9]/g, '_')
}

function isSelected(instanceId, dbName, tableName) {
  const s = selectedTable.value
  if (!s) return false
  return s.instanceId === instanceId && s.dbName === dbName && s.tableName === tableName
}

onMounted(async () => {
  const res = await apiGetPostgres()
  const all = res && res.ok ? await res.json() : []
  instances.value = all.filter(i => i.status === 'running')
  loadingInstances.value = false
})

async function toggleInstance(inst) {
  const id = inst.id
  if (openInstances.value[id]) {
    openInstances.value[id] = false
    return
  }
  openInstances.value[id] = true
  if (dbs.value[id] !== undefined) return
  loadingDbs.value[id] = true
  const res = await apiGetDatabases(id)
  dbs.value[id] = res && res.ok ? await res.json() : []
  loadingDbs.value[id] = false
}

async function toggleDb(inst, db) {
  const key = catId(inst.id, db.name)
  if (openDbs.value[key]) {
    openDbs.value[key] = false
    return
  }
  openDbs.value[key] = true
  if (tables.value[key] !== undefined) return
  loadingTables.value[key] = true
  const res = await apiGetTables(inst.id, db.name)
  tables.value[key] = res && res.ok ? await res.json() : []
  loadingTables.value[key] = false
}

function selectTable(inst, db, t) {
  selectedTable.value = { instanceId: inst.id, instanceName: inst.name, dbName: db.name, tableName: t.name }
  emit('select-table', {
    instanceId: inst.id,
    instanceName: inst.name,
    dbName: db.name,
    tableName: t.name,
  })
}

function clearSelection() {
  selectedTable.value = null
}

defineExpose({ clearSelection })
</script>
