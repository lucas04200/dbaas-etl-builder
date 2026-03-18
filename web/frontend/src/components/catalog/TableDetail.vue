<template>
  <div class="table-detail">
    <div class="table-breadcrumb">
      <span class="bc-instance" @click="$emit('clear-selection')">{{ instanceName }}</span>
      <span class="bc-sep">›</span>
      <span class="bc-db" @click="$emit('clear-selection')">{{ dbName }}</span>
      <span class="bc-sep">›</span>
      <span class="bc-table">{{ tableName }}</span>
    </div>
    <div class="tabs">
      <div :class="['tab', { active: activeTab === 'overview' }]" @click="activeTab = 'overview'">Aperçu</div>
      <div :class="['tab', { active: activeTab === 'sample' }]" @click="activeTab = 'sample'">Données</div>
    </div>
    <div>
      <OverviewTab
        v-if="activeTab === 'overview'"
        :instance-id="instanceId"
        :db-name="dbName"
        :table-name="tableName"
      />
      <SampleTab
        v-else
        :instance-id="instanceId"
        :db-name="dbName"
        :table-name="tableName"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import OverviewTab from './OverviewTab.vue'
import SampleTab from './SampleTab.vue'

const props = defineProps({
  instanceId: Number,
  instanceName: String,
  dbName: String,
  tableName: String,
})
defineEmits(['clear-selection'])

const activeTab = ref('overview')

watch(() => props.tableName, () => {
  activeTab.value = 'overview'
})
</script>
