<template>
  <div class="tree-node">
    <!-- Instance row -->
    <div :class="['tree-item', { 'tree-internal': isInternal }]" @click="$emit('toggle-instance', inst)">
      <svg :class="['tree-chevron', { open: openInstances[inst.id] }]" width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style="flex-shrink:0">
        <ellipse cx="7" cy="3.2" rx="4.5" ry="1.6" :stroke="isInternal ? '#9CA3AF' : '#4C6EF5'" stroke-width="1.2"/>
        <path d="M2.5 3.2v3.6c0 .9 2 1.6 4.5 1.6s4.5-.7 4.5-1.6V3.2" :stroke="isInternal ? '#9CA3AF' : '#4C6EF5'" stroke-width="1.2"/>
        <path d="M2.5 6.8v3.6c0 .9 2 1.6 4.5 1.6s4.5-.7 4.5-1.6V6.8" :stroke="isInternal ? '#9CA3AF' : '#4C6EF5'" stroke-width="1.2"/>
      </svg>
      <span class="tree-label" :style="isInternal ? 'color:#9CA3AF;font-weight:500' : 'font-weight:600'">{{ inst.name }}</span>
      <span v-if="isInternal" class="tree-badge-internal">interne</span>
      <span v-else class="tree-meta">:{{ inst.host_port }}</span>
    </div>

    <!-- Databases -->
    <div v-if="openInstances[inst.id]">
      <div v-if="loadingDbs[inst.id]" class="tree-empty" style="padding-left:26px">Chargement…</div>
      <div v-else-if="dbs[inst.id] && !dbs[inst.id].length" class="tree-empty" style="padding-left:26px">Aucune base</div>
      <template v-else>
        <div v-for="db in (dbs[inst.id] || [])" :key="db.name" class="tree-node">
          <div class="tree-item tree-l1" @click="$emit('toggle-db', inst, db)">
            <svg :class="['tree-chevron', { open: openDbs[catKey(inst.id, db.name)] }]" width="11" height="11" viewBox="0 0 12 12" fill="none">
              <path d="M4 2l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style="flex-shrink:0">
              <circle cx="6.5" cy="6.5" r="5" stroke="#6B7280" stroke-width="1.2"/>
              <path d="M6.5 1.5v11M1.5 6.5h10" stroke="#6B7280" stroke-width="1.2"/>
            </svg>
            <span class="tree-label">{{ db.name }}</span>
            <span v-if="db.size" class="tree-meta">{{ db.size }}</span>
          </div>

          <div v-if="openDbs[catKey(inst.id, db.name)]">
            <div v-if="loadingTables[catKey(inst.id, db.name)]" class="tree-empty" style="padding-left:40px">Chargement…</div>
            <div v-else-if="tables[catKey(inst.id, db.name)] && !tables[catKey(inst.id, db.name)].length" class="tree-empty" style="padding-left:40px">Aucune table</div>
            <template v-else>
              <div
                v-for="t in (tables[catKey(inst.id, db.name)] || [])"
                :key="t.name"
                :class="['tree-item', 'tree-l2', { selected: isSelected(inst.id, db.name, t.name) }]"
                @click="$emit('select-table', inst, db, t)"
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
            </template>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  inst:          { type: Object, required: true },
  openInstances: { type: Object, required: true },
  dbs:           { type: Object, required: true },
  loadingDbs:    { type: Object, required: true },
  openDbs:       { type: Object, required: true },
  tables:        { type: Object, required: true },
  loadingTables: { type: Object, required: true },
  selectedTable: { type: Object, default: null },
  isInternal:    { type: Boolean, default: false },
})

defineEmits(['toggle-instance', 'toggle-db', 'select-table'])

function catKey(...parts) {
  return parts.map(String).join('__').replace(/[^a-zA-Z0-9]/g, '_')
}

function isSelected(instanceId, dbName, tableName) {
  const s = props.selectedTable
  return !!(s && s.instanceId === instanceId && s.dbName === dbName && s.tableName === tableName)
}
</script>
