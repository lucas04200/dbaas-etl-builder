<template>
  <div class="groups-layout">
    <!-- Left: group list -->
    <div class="groups-list">
      <div class="groups-list-head">
        <span style="font-size:13px;font-weight:600;color:var(--text-primary)">Groupes</span>
        <button class="btn btn-primary btn-sm" @click="toggleCreate">+ Nouveau</button>
      </div>

      <!-- Create panel -->
      <div v-if="showCreate" class="groups-create-panel">
        <!-- Step 1: pick instance -->
        <template v-if="createStep === 1">
          <div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">Étape 1 — Instance cible</div>
          <div v-if="loadingInstances" style="font-size:12px;color:#9CA3AF;padding:8px 0">Chargement…</div>
          <div v-else-if="!instances.length" style="font-size:12px;color:#9CA3AF;padding:8px 0">
            Aucune instance en cours d'exécution
          </div>
          <template v-else>
            <div class="form-group" style="margin-bottom:8px">
              <label>Type</label>
              <select v-model="newInstType" @change="newInstId = ''">
                <option value="" disabled>Choisir un type…</option>
                <option v-for="t in instanceTypes" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
            <div v-if="newInstType" class="form-group" style="margin-bottom:10px">
              <label>Instance</label>
              <select v-model="newInstId">
                <option value="" disabled>Choisir une instance…</option>
                <option v-for="inst in filteredInstances" :key="inst.id" :value="inst.id">{{ inst.name }}</option>
              </select>
            </div>
            <div style="display:flex;gap:6px">
              <button class="btn btn-primary btn-sm" :disabled="!newInstId" @click="createStep = 2">Suivant →</button>
              <button class="btn btn-secondary btn-sm" @click="cancelCreate">Annuler</button>
            </div>
          </template>
        </template>

        <!-- Step 2: name the group -->
        <template v-else>
          <div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px">Étape 2 — Nommer le groupe</div>
          <div class="instance-badge" style="margin-bottom:10px">
            <span class="badge" :class="`badge-type-${newInstType}`">{{ newInstType }}</span>
            <span style="font-size:12px;font-weight:500">{{ selectedInstanceName }}</span>
          </div>
          <div class="form-group" style="margin-bottom:8px">
            <label>Nom du groupe</label>
            <input type="text" v-model="groupName" placeholder="ex : analysts" @keyup.enter="createGroup" autofocus />
          </div>
          <div class="form-group" style="margin-bottom:10px">
            <label>Description (optionnel)</label>
            <input type="text" v-model="groupDesc" placeholder="ex : Équipe analytique" @keyup.enter="createGroup" />
          </div>
          <div style="display:flex;gap:6px">
            <button class="btn btn-secondary btn-sm" @click="createStep = 1">← Retour</button>
            <button class="btn btn-primary btn-sm" :disabled="createLoading || !groupName.trim()" @click="createGroup">Créer</button>
            <button class="btn btn-ghost btn-sm" @click="cancelCreate">Annuler</button>
          </div>
        </template>
      </div>

      <div v-if="loadingGroups" class="loading" style="padding:12px">Chargement…</div>
      <div v-else-if="!groups.length" class="empty" style="padding:12px;font-size:12px;color:#9CA3AF">Aucun groupe</div>
      <div v-else class="groups-list-items">
        <div
          v-for="g in groups"
          :key="g.id"
          :class="['group-list-item', { selected: selectedGroup?.id === g.id }]"
          @click="selectGroup(g)"
        >
          <div style="flex:1;min-width:0">
            <div class="group-list-item-name">{{ g.name }}</div>
            <div class="group-list-item-meta">
              <span v-if="g.instance_type" class="badge" :class="`badge-type-${g.instance_type}`" style="margin-right:4px">{{ g.instance_type }}</span>
              <span>{{ g.instance_name || '—' }}</span>
              <span style="margin-left:6px">· {{ g.member_count }} membre(s)</span>
            </div>
          </div>
          <button class="btn btn-ghost btn-sm" @click.stop="deleteGroup(g)" title="Supprimer">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Right: detail -->
    <div class="groups-detail">
      <div v-if="!selectedGroup" class="groups-empty">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" style="opacity:.25">
          <circle cx="14" cy="14" r="7" stroke="#4C6EF5" stroke-width="2"/>
          <circle cx="26" cy="14" r="7" stroke="#4C6EF5" stroke-width="2"/>
          <path d="M4 34c0-5.5 4.5-10 10-10h12c5.5 0 10 4.5 10 10" stroke="#4C6EF5" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <p style="font-size:13px">Sélectionnez un groupe</p>
      </div>
      <div v-else-if="loadingDetail" class="loading" style="padding:28px">Chargement…</div>
      <GroupDetail
        v-else-if="groupDetail"
        :key="selectedGroup.id"
        :group="selectedGroup"
        :detail="groupDetail"
        @reload="reloadDetail"
      />

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useToastStore } from '../../stores/toast.js'
import { apiGetGroups, apiCreateGroup, apiDeleteGroup, apiGetGroupMembers, apiGetUsers, apiGetInstances } from '../../lib/api.js'
import GroupDetail from './GroupDetail.vue'

const toastStore = useToastStore()

const groups = ref([])
const loadingGroups = ref(true)
const groupName = ref('')
const groupDesc = ref('')
const createLoading = ref(false)
const showCreate = ref(false)
const createStep = ref(1)
const selectedGroup = ref(null)
const groupDetail = ref(null)
const loadingDetail = ref(false)

const instances = ref([])
const loadingInstances = ref(false)
const newInstType = ref('')
const newInstId = ref('')

const instanceTypes = computed(() => [...new Set(instances.value.map(i => i.type))])
const filteredInstances = computed(() => instances.value.filter(i => i.type === newInstType.value))
const selectedInstanceName = computed(() => instances.value.find(i => i.id === newInstId.value)?.name || '')

async function openCreate() {
  showCreate.value = true
  createStep.value = 1
  newInstType.value = ''
  newInstId.value = ''
  groupName.value = ''
  groupDesc.value = ''
  if (!instances.value.length) {
    loadingInstances.value = true
    const res = await apiGetInstances()
    instances.value = res && res.ok ? await res.json() : []
    loadingInstances.value = false
  }
}

function cancelCreate() {
  showCreate.value = false
  createStep.value = 1
  newInstType.value = ''
  newInstId.value = ''
  groupName.value = ''
  groupDesc.value = ''
}

// Override + button to trigger openCreate
function toggleCreate() {
  if (showCreate.value) cancelCreate()
  else openCreate()
}

async function loadGroups() {
  loadingGroups.value = true
  const res = await apiGetGroups()
  groups.value = res && res.ok ? await res.json() : []
  loadingGroups.value = false
}

async function createGroup() {
  if (!groupName.value.trim()) { toastStore.showToast('Entrez un nom', true); return }
  createLoading.value = true
  const res = await apiCreateGroup({
    name: groupName.value.trim(),
    description: groupDesc.value,
    instance_type: newInstType.value,
    instance_id: newInstId.value,
  })
  createLoading.value = false
  if (res && res.ok) {
    const created = await res.json()
    toastStore.showToast(`Groupe « ${groupName.value} » créé`)
    cancelCreate()
    await loadGroups()
    selectGroup(groups.value.find(g => g.id === created.id) || groups.value.at(-1))
  } else {
    const d = await res?.json().catch(() => ({}))
    toastStore.showToast(d.detail || 'Erreur', true)
  }
}

async function deleteGroup(g) {
  if (!confirm(`Supprimer le groupe « ${g.name} » ?`)) return
  const res = await apiDeleteGroup(g.id)
  if (res && res.ok) {
    toastStore.showToast('Groupe supprimé')
    if (selectedGroup.value?.id === g.id) { selectedGroup.value = null; groupDetail.value = null }
    await loadGroups()
  } else {
    toastStore.showToast('Erreur', true)
  }
}

async function selectGroup(g) {
  if (!g) return
  selectedGroup.value = g
  groupDetail.value = null
  loadingDetail.value = true
  const [mRes, uRes] = await Promise.all([
    apiGetGroupMembers(g.id),
    apiGetUsers(),
  ])
  groupDetail.value = {
    members: mRes && mRes.ok ? await mRes.json() : [],
    allUsers: uRes && uRes.ok ? await uRes.json() : [],
  }
  loadingDetail.value = false
}

async function reloadDetail() {
  if (selectedGroup.value) await selectGroup(selectedGroup.value)
}

loadGroups()
</script>

<style scoped>
.instance-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--content-bg, #F9FAFB);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
}
</style>
