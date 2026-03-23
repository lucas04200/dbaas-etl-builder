<template>
  <div class="catalog-layout">
    <CatalogTree ref="treeRef" @select-table="onSelectTable" @clear-selection="clearSelection" />
    <div class="catalog-content">
      <TableDetail
        v-if="selected"
        :instance-id="selected.instanceId"
        :instance-name="selected.instanceName"
        :db-name="selected.dbName"
        :table-name="selected.tableName"
        @clear-selection="clearSelection"
      />
      <div v-else class="catalog-empty">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" style="opacity:.3">
          <rect x="6" y="6" width="15" height="15" rx="3" stroke="#4C6EF5" stroke-width="2"/>
          <rect x="27" y="6" width="15" height="15" rx="3" stroke="#4C6EF5" stroke-width="2"/>
          <rect x="6" y="27" width="15" height="15" rx="3" stroke="#4C6EF5" stroke-width="2"/>
          <rect x="27" y="27" width="15" height="15" rx="3" stroke="#4C6EF5" stroke-width="2"/>
        </svg>
        <p style="font-size:14px">Sélectionnez une table dans le catalogue</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import CatalogTree from '../components/catalog/CatalogTree.vue'
import TableDetail from '../components/catalog/TableDetail.vue'

const treeRef = ref(null)
const selected = ref(null)

function onSelectTable(info) {
  selected.value = info
}

function clearSelection() {
  selected.value = null
  if (treeRef.value) treeRef.value.clearSelection()
}
</script>
