<template>
  <div class="catalog-tree">
    <div class="catalog-tree-head">Sources de données</div>
    <div class="catalog-tree-body">

      <div v-if="loadingInstances" class="tree-loading">Chargement…</div>
      <div v-else-if="!instances.length && !internalInstances.length" class="tree-empty">
        Aucune instance active.<br>Déployez d'abord une base de données.
      </div>

      <template v-else>
        <!-- Instances principales -->
        <InstanceTreeNode
          v-for="inst in instances"
          :key="inst.id"
          :inst="inst"
          :open-instances="openInstances"
          :dbs="dbs"
          :loading-dbs="loadingDbs"
          :open-dbs="openDbs"
          :tables="tables"
          :loading-tables="loadingTables"
          :selected-table="selectedTable"
          @toggle-instance="toggleInstance"
          @toggle-db="toggleDb"
          @select-table="selectTable"
        />

        <!-- Section Avancé -->
        <template v-if="internalInstances.length">
          <div class="advanced-separator" @click="showAdvanced = !showAdvanced">
            <svg :class="['adv-chevron', { open: showAdvanced }]" width="11" height="11" viewBox="0 0 12 12" fill="none">
              <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>Avancé</span>
            <span class="adv-count">{{ internalInstances.length }}</span>
          </div>
          <template v-if="showAdvanced">
            <InstanceTreeNode
              v-for="inst in internalInstances"
              :key="'int_' + inst.id"
              :inst="inst"
              :open-instances="openInstances"
              :dbs="dbs"
              :loading-dbs="loadingDbs"
              :open-dbs="openDbs"
              :tables="tables"
              :loading-tables="loadingTables"
              :selected-table="selectedTable"
              :is-internal="true"
              @toggle-instance="toggleInstance"
              @toggle-db="toggleDb"
              @select-table="selectTable"
            />
          </template>
        </template>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiGetPostgres, apiGetInternalPostgres, apiGetDatabases, apiGetTables } from '../../lib/api.js'
import InstanceTreeNode from './InstanceTreeNode.vue'

const emit = defineEmits(['select-table', 'clear-selection'])

const instances         = ref([])
const internalInstances = ref([])
const loadingInstances  = ref(true)
const showAdvanced      = ref(false)

const openInstances  = ref({})
const dbs            = ref({})
const loadingDbs     = ref({})
const openDbs        = ref({})
const tables         = ref({})
const loadingTables  = ref({})
const selectedTable  = ref(null)

function catKey(...parts) {
  return parts.map(String).join('__').replace(/[^a-zA-Z0-9]/g, '_')
}

onMounted(async () => {
  const [res, resInt] = await Promise.all([apiGetPostgres(), apiGetInternalPostgres()])
  const all    = res    && res.ok    ? await res.json()    : []
  const allInt = resInt && resInt.ok ? await resInt.json() : []
  instances.value         = all.filter(i => i.status === 'running')
  internalInstances.value = allInt.filter(i => i.status === 'running')
  loadingInstances.value  = false
})

async function toggleInstance(inst) {
  const id = inst.id
  if (openInstances.value[id]) { openInstances.value[id] = false; return }
  openInstances.value[id] = true
  if (dbs.value[id] !== undefined) return
  loadingDbs.value[id] = true
  const res = await apiGetDatabases(id)
  dbs.value[id] = res && res.ok ? await res.json() : []
  loadingDbs.value[id] = false
}

async function toggleDb(inst, db) {
  const key = catKey(inst.id, db.name)
  if (openDbs.value[key]) { openDbs.value[key] = false; return }
  openDbs.value[key] = true
  if (tables.value[key] !== undefined) return
  loadingTables.value[key] = true
  const res = await apiGetTables(inst.id, db.name)
  tables.value[key] = res && res.ok ? await res.json() : []
  loadingTables.value[key] = false
}

function selectTable(inst, db, t) {
  selectedTable.value = { instanceId: inst.id, instanceName: inst.name, dbName: db.name, tableName: t.name }
  emit('select-table', selectedTable.value)
}

function clearSelection() { selectedTable.value = null }
defineExpose({ clearSelection })
</script>

<style>
.catalog-tree {
  width: 268px; flex-shrink: 0;
  border-right: 1px solid var(--border);
  background: var(--white);
  display: flex; flex-direction: column; overflow: hidden;
}
.catalog-tree-head {
  padding: 14px 18px 10px;
  font-size: 11px; font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.8px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.catalog-tree-body { flex: 1; overflow-y: auto; padding: 6px 0; }
.tree-loading { padding: 10px 18px; font-size: 13px; color: #9CA3AF; }
.tree-empty { font-size: 12.5px; color: #9CA3AF; padding: 8px 18px; line-height: 1.5; }

.tree-node {}
.tree-item {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 10px 5px 14px; margin: 0 5px;
  border-radius: 6px; cursor: pointer; user-select: none;
  font-size: 13px; color: var(--text-primary);
  transition: background 0.1s;
}
.tree-item:hover  { background: var(--content-bg); }
.tree-item.selected { background: var(--accent-dim); color: var(--accent); }
.tree-item.tree-internal { opacity: 0.75; }
.tree-l1 { padding-left: 28px; font-size: 12.5px; }
.tree-l2 { padding-left: 42px; font-size: 12px; }
.tree-chevron { color: #9CA3AF; flex-shrink: 0; transition: transform 0.15s; }
.tree-chevron.open { transform: rotate(90deg); }
.tree-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tree-meta  { font-size: 11px; color: #9CA3AF; flex-shrink: 0; }
.tree-badge-internal {
  font-size: 9.5px; font-weight: 600;
  background: #F3F4F6; color: #9CA3AF;
  border: 1px solid #E5E7EB;
  padding: 1px 5px; border-radius: 10px; flex-shrink: 0;
}

.advanced-separator {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 14px 4px;
  margin-top: 8px;
  border-top: 1px solid var(--border);
  cursor: pointer;
  font-size: 10px; font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.7px;
  user-select: none;
}
.advanced-separator:hover { color: var(--text-secondary); }
.adv-chevron { color: var(--text-muted); transition: transform 0.15s; }
.adv-chevron.open { transform: rotate(90deg); }
.adv-count {
  margin-left: auto;
  background: #F3F4F6; color: #9CA3AF;
  font-size: 10px; font-weight: 600;
  padding: 0 5px; border-radius: 10px;
}
</style>
