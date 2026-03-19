<template>
  <div class="groups-layout">
    <!-- Left: group list -->
    <div class="groups-list">
      <div class="groups-list-head">
        <span style="font-size:13px;font-weight:600;color:var(--text-primary)">Groupes</span>
        <button class="btn btn-primary btn-sm" @click="showCreate = !showCreate">+ Nouveau</button>
      </div>

      <div v-if="showCreate" class="groups-create-panel">
        <div class="form-group" style="margin-bottom:8px">
          <label>Nom</label>
          <input type="text" v-model="groupName" placeholder="ex : analysts" @keyup.enter="createGroup" autofocus />
        </div>
        <div class="form-group" style="margin-bottom:10px">
          <label>Description (optionnel)</label>
          <input type="text" v-model="groupDesc" placeholder="ex : Équipe analytique" @keyup.enter="createGroup" />
        </div>
        <div style="display:flex;gap:6px">
          <button class="btn btn-primary btn-sm" :disabled="createLoading" @click="createGroup">Créer</button>
          <button class="btn btn-secondary btn-sm" @click="showCreate = false; groupName = ''; groupDesc = ''">Annuler</button>
        </div>
      </div>

      <div v-if="loadingGroups" class="loading" style="padding:12px">Chargement…</div>
      <div v-else-if="!groups.length" class="empty" style="padding:12px">Aucun groupe</div>
      <div v-else class="groups-list-items">
        <div
          v-for="g in groups"
          :key="g.id"
          :class="['group-list-item', { selected: selectedGroup?.id === g.id }]"
          @click="selectGroup(g)"
        >
          <div style="flex:1;min-width:0">
            <div class="group-list-item-name">{{ g.name }}</div>
            <div class="group-list-item-meta">{{ g.member_count }} membre(s){{ g.description ? ' · ' + g.description : '' }}</div>
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
        :group-id="selectedGroup.id"
        :group-name="selectedGroup.name"
        :detail="groupDetail"
        @reload="reloadDetail"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useToastStore } from '../../stores/toast.js'
import { apiGetGroups, apiCreateGroup, apiDeleteGroup, apiGetGroupMembers, apiGetGroupPermissions, apiGetUsers, apiGetPostgres, apiGetN8n } from '../../lib/api.js'
import GroupDetail from './GroupDetail.vue'

const toastStore = useToastStore()

const groups = ref([])
const loadingGroups = ref(true)
const groupName = ref('')
const groupDesc = ref('')
const createLoading = ref(false)
const showCreate = ref(false)
const selectedGroup = ref(null)
const groupDetail = ref(null)
const loadingDetail = ref(false)

async function loadGroups() {
  loadingGroups.value = true
  const res = await apiGetGroups()
  groups.value = res && res.ok ? await res.json() : []
  loadingGroups.value = false
}

async function createGroup() {
  if (!groupName.value.trim()) { toastStore.showToast('Entrez un nom', true); return }
  createLoading.value = true
  const res = await apiCreateGroup({ name: groupName.value.trim(), description: groupDesc.value })
  createLoading.value = false
  if (res && res.ok) {
    const created = await res.json()
    toastStore.showToast(`Groupe « ${groupName.value} » créé`)
    groupName.value = ''; groupDesc.value = ''; showCreate.value = false
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
  const [mRes, pRes, uRes, pgRes, n8nRes] = await Promise.all([
    apiGetGroupMembers(g.id),
    apiGetGroupPermissions(g.id),
    apiGetUsers(),
    apiGetPostgres(),
    apiGetN8n(),
  ])
  groupDetail.value = {
    members: mRes && mRes.ok ? await mRes.json() : [],
    perms: pRes && pRes.ok ? await pRes.json() : [],
    allUsers: uRes && uRes.ok ? await uRes.json() : [],
    pgs: pgRes && pgRes.ok ? await pgRes.json() : [],
    n8ns: n8nRes && n8nRes.ok ? await n8nRes.json() : [],
  }
  loadingDetail.value = false
}

async function reloadDetail() {
  if (selectedGroup.value) await selectGroup(selectedGroup.value)
}

loadGroups()
</script>
