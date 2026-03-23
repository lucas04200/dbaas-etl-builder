<template>
  <div>
    <p style="color:#6B7280;font-size:13.5px;margin-bottom:18px">
      Visualisez les identifiants chiffrés de vos instances. Chaque consultation est enregistrée dans le journal d'audit.
    </p>

    <div class="svc-selector">
      <label>Type de service</label>
      <select v-model="selectedType" @change="selectedInstance = null; revealed = null">
        <option value="">— Choisir un type —</option>
        <option v-for="svc in serviceTypes" :key="svc.key" :value="svc.key">{{ svc.label }}</option>
      </select>
    </div>

    <div v-if="selectedType && instances.length" class="instance-list">
      <div
        v-for="inst in instances" :key="inst.id"
        :class="['instance-row', { selected: selectedInstance?.id === inst.id }]"
        @click="selectInstance(inst)"
      >
        <span class="inst-name">{{ inst.name }}</span>
        <span class="inst-status" :class="inst.status">{{ inst.status }}</span>
        <span class="inst-port">:{{ inst.host_port }}</span>
      </div>
    </div>

    <div v-if="selectedType && !instances.length && !loadingInstances" class="empty-msg">
      Aucune instance de ce type.
    </div>

    <div v-if="loadingInstances" class="empty-msg">Chargement...</div>

    <div v-if="selectedInstance" style="margin-top:18px">
      <button class="btn btn-primary" :disabled="loadingCreds" @click="revealCreds">
        {{ loadingCreds ? 'Déchiffrement…' : 'Révéler les identifiants' }}
      </button>
    </div>

    <div v-if="revealed" class="cred-result">
      <div v-for="(value, key) in revealed" :key="key" class="cred-row">
        <span class="cred-label">{{ key }}</span>
        <div class="cred-value-wrap">
          <code class="cred-value">{{ value }}</code>
          <button class="cred-copy" @click="copy(value)">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.3"/>
              <path d="M3 11V3a1.5 1.5 0 011.5-1.5H11" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <div v-if="revealError" class="error-msg">{{ revealError }}</div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import {
  apiGetPostgres, apiGetRedis, apiGetMinIO, apiGetMariaDB,
  apiGetClickHouse, apiGetSuperset, apiGetAirflow, apiGetHasura,
  apiGetMage, apiRevealCredentials,
} from '../../lib/api.js'
import { useToastStore } from '../../stores/toast.js'

const toastStore = useToastStore()

const serviceTypes = [
  { key: 'postgres', label: 'PostgreSQL', fetch: apiGetPostgres },
  { key: 'redis', label: 'Redis', fetch: apiGetRedis },
  { key: 'minio', label: 'MinIO', fetch: apiGetMinIO },
  { key: 'mariadb', label: 'MariaDB', fetch: apiGetMariaDB },
  { key: 'clickhouse', label: 'ClickHouse', fetch: apiGetClickHouse },
  { key: 'superset', label: 'Superset', fetch: apiGetSuperset },
  { key: 'airflow', label: 'Airflow', fetch: apiGetAirflow },
  { key: 'hasura', label: 'Hasura', fetch: apiGetHasura },
  { key: 'mage', label: 'Mage', fetch: apiGetMage },
]

const selectedType = ref('')
const instances = ref([])
const loadingInstances = ref(false)
const selectedInstance = ref(null)
const loadingCreds = ref(false)
const revealed = ref(null)
const revealError = ref('')

watch(selectedType, async (type) => {
  instances.value = []
  revealed.value = null
  revealError.value = ''
  if (!type) return
  const svc = serviceTypes.find(s => s.key === type)
  if (!svc) return
  loadingInstances.value = true
  try {
    const res = await svc.fetch()
    instances.value = res && res.ok ? await res.json() : []
  } finally {
    loadingInstances.value = false
  }
})

function selectInstance(inst) {
  selectedInstance.value = inst
  revealed.value = null
  revealError.value = ''
}

async function revealCreds() {
  if (!selectedInstance.value) return
  loadingCreds.value = true
  revealError.value = ''
  try {
    const res = await apiRevealCredentials(selectedType.value, selectedInstance.value.id)
    if (res && res.ok) {
      revealed.value = await res.json()
    } else {
      const d = await res?.json().catch(() => ({}))
      revealError.value = d.detail || 'Erreur lors du déchiffrement'
    }
  } catch {
    revealError.value = 'Erreur réseau'
  } finally {
    loadingCreds.value = false
  }
}

async function copy(text) {
  try {
    await navigator.clipboard.writeText(String(text))
    toastStore.showToast('Copié')
  } catch {
    toastStore.showToast('Impossible de copier', true)
  }
}
</script>

<style scoped>
.svc-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.svc-selector label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}
.svc-selector select {
  padding: 7px 10px;
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  font-size: 13px;
  min-width: 200px;
}
.instance-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 260px;
  overflow-y: auto;
}
.instance-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.1s;
}
.instance-row:hover { background: #F9FAFB; }
.instance-row.selected {
  background: #EEF2FF;
  border-color: #A5B4FC;
}
.inst-name {
  font-size: 13.5px;
  font-weight: 500;
  flex: 1;
}
.inst-status {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  padding: 2px 7px;
  border-radius: 4px;
}
.inst-status.running { color: #059669; background: #ECFDF5; }
.inst-status.provisioning { color: #D97706; background: #FFFBEB; }
.inst-status.error { color: #DC2626; background: #FEF2F2; }
.inst-port {
  font-size: 12px;
  color: #9CA3AF;
  font-family: monospace;
}
.cred-result {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cred-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 8px 12px;
}
.cred-label {
  font-size: 13px;
  color: #6B7280;
  min-width: 130px;
}
.cred-value-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cred-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: #111827;
  user-select: all;
}
.cred-copy {
  background: none;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  padding: 3px 5px;
  cursor: pointer;
  color: #6B7280;
  display: flex;
  align-items: center;
}
.cred-copy:hover { background: #F3F4F6; color: #374151; }
.empty-msg {
  font-size: 13px;
  color: #9CA3AF;
  padding: 12px 0;
}
.error-msg {
  margin-top: 12px;
  color: #DC2626;
  font-size: 13px;
}
</style>
