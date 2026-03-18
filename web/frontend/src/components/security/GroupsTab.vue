<template>
  <div>
    <div class="card">
      <div class="card-title">Créer un groupe</div>
      <div class="form-row" style="grid-template-columns:1fr 2fr auto">
        <div class="form-group">
          <label>Nom</label>
          <input type="text" v-model="groupName" placeholder="ex : analysts">
        </div>
        <div class="form-group">
          <label>Description (optionnel)</label>
          <input type="text" v-model="groupDesc" placeholder="ex : Équipe analytique">
        </div>
        <button class="btn btn-primary" :disabled="createLoading" @click="createGroup">Créer</button>
      </div>
    </div>

    <div v-if="loadingGroups" class="loading">Chargement…</div>
    <div v-else-if="!groups.length" class="empty">Aucun groupe</div>
    <div v-else>
      <div v-for="g in groups" :key="g.id" class="accordion-item">
        <div class="accordion-head" @click="toggleGroup(g.id)">
          <div class="accordion-head-left">
            <div>
              <div class="accordion-head-name">{{ g.name }}</div>
              <div class="accordion-head-meta">{{ g.description ? g.description + ' · ' : '' }}{{ g.member_count }} membre(s)</div>
            </div>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <button class="btn btn-ghost btn-sm" @click.stop="deleteGroup(g)">Supprimer</button>
            <svg :class="['accordion-chevron', { open: openGroups[g.id] }]" width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M5 3l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </div>
        <div :class="['accordion-body', { open: openGroups[g.id] }]">
          <div v-if="loadingDetail[g.id]" class="loading">Chargement…</div>
          <GroupDetail
            v-else-if="groupDetails[g.id]"
            :group-id="g.id"
            :detail="groupDetails[g.id]"
            @reload="loadGroupDetail(g.id)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useToastStore } from '../../stores/toast.js'
import { apiGetGroups, apiCreateGroup, apiDeleteGroup, apiGetGroupMembers, apiGetGroupPermissions, apiGetUsers, apiGetPostgres, apiGetN8n } from '../../lib/api.js'
import GroupDetail from './GroupDetail.vue'

const toastStore = useToastStore()

const groups = ref([])
const loadingGroups = ref(true)
const groupName = ref('')
const groupDesc = ref('')
const createLoading = ref(false)
const openGroups = reactive({})
const groupDetails = reactive({})
const loadingDetail = reactive({})

async function loadGroups() {
  const res = await apiGetGroups()
  if (!res || !res.ok) { loadingGroups.value = false; return }
  groups.value = await res.json()
  loadingGroups.value = false
}

async function createGroup() {
  if (!groupName.value) { toastStore.showToast('Entrez un nom', true); return }
  createLoading.value = true
  const res = await apiCreateGroup({ name: groupName.value, description: groupDesc.value })
  createLoading.value = false
  if (res && res.ok) {
    toastStore.showToast(`Groupe « ${groupName.value} » créé`)
    groupName.value = ''; groupDesc.value = ''
    await loadGroups()
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
    await loadGroups()
  } else {
    toastStore.showToast('Erreur', true)
  }
}

async function toggleGroup(id) {
  if (openGroups[id]) {
    openGroups[id] = false
    return
  }
  openGroups[id] = true
  if (!groupDetails[id]) {
    await loadGroupDetail(id)
  }
}

async function loadGroupDetail(id) {
  loadingDetail[id] = true
  const [mRes, pRes, uRes, pgRes, n8nRes] = await Promise.all([
    apiGetGroupMembers(id),
    apiGetGroupPermissions(id),
    apiGetUsers(),
    apiGetPostgres(),
    apiGetN8n(),
  ])
  const members = mRes && mRes.ok ? await mRes.json() : []
  const perms = pRes && pRes.ok ? await pRes.json() : []
  const allUsers = uRes && uRes.ok ? await uRes.json() : []
  const pgs = pgRes && pgRes.ok ? await pgRes.json() : []
  const n8ns = n8nRes && n8nRes.ok ? await n8nRes.json() : []

  groupDetails[id] = { members, perms, allUsers, pgs, n8ns }
  loadingDetail[id] = false
}

onMounted(loadGroups)
</script>
