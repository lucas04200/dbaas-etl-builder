<template>
  <div class="group-detail">
    <div class="group-detail-head">
      <h3 class="group-detail-title">{{ groupName }}</h3>
    </div>

    <!-- Members -->
    <div class="group-detail-section">
      <div class="group-detail-section-title">Membres</div>
      <div class="pill-list" style="margin-bottom:10px">
        <span v-if="!detail.members.length" style="font-size:12px;color:#9CA3AF">Aucun membre</span>
        <span v-for="m in detail.members" :key="m.id" class="pill">
          {{ m.username }}
          <button class="pill-remove" @click="removeMember(m.id)">×</button>
        </span>
      </div>
      <div v-if="availUsers.length" class="add-inline-form">
        <select v-model="selectedUser">
          <option value="" disabled>Choisir un utilisateur…</option>
          <option v-for="u in availUsers" :key="u.id" :value="u.id">{{ u.username }}</option>
        </select>
        <button class="btn btn-secondary btn-sm" @click="addMember" :disabled="!selectedUser">Ajouter</button>
      </div>
      <div v-else-if="detail.allUsers.length && !availUsers.length" style="font-size:12px;color:#9CA3AF;margin-top:6px">
        Tous les utilisateurs sont déjà membres
      </div>
    </div>

    <!-- Permissions -->
    <div class="group-detail-section">
      <div class="group-detail-section-title">Permissions</div>

      <table v-if="detail.perms.length" class="perm-table">
        <thead>
          <tr>
            <th>Instance</th>
            <th>Type</th>
            <th>Niveau</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in detail.perms" :key="p.id">
            <td>{{ p.instance_name }}</td>
            <td><span class="badge" :class="p.instance_type === 'postgres' ? 'badge-admin' : 'badge-user'">{{ p.instance_type }}</span></td>
            <td><span class="badge" :class="`pill-perm ${p.permission}`">{{ p.permission }}</span></td>
            <td><button class="btn btn-ghost btn-sm" @click="removePerm(p.id)">Retirer</button></td>
          </tr>
        </tbody>
      </table>
      <div v-else style="font-size:12px;color:#9CA3AF;margin-bottom:10px">Aucune permission</div>

      <div v-if="allInstances.length" class="add-inline-form" style="margin-top:10px">
        <select v-model="selectedInst">
          <option value="" disabled>Choisir une instance…</option>
          <option v-for="inst in allInstances" :key="inst.value" :value="inst.value">{{ inst.label }}</option>
        </select>
        <select v-model="selectedLevel" style="width:120px">
          <option value="read">Lecture</option>
          <option value="write">Écriture</option>
          <option value="admin">Admin</option>
        </select>
        <button class="btn btn-secondary btn-sm" @click="addPerm" :disabled="!selectedInst">Ajouter</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useToastStore } from '../../stores/toast.js'
import { apiAddGroupMember, apiRemoveGroupMember, apiAddGroupPermission, apiRemoveGroupPermission } from '../../lib/api.js'

const props = defineProps({
  groupId: Number,
  groupName: String,
  detail: Object,
})
const emit = defineEmits(['reload'])
const toastStore = useToastStore()

const availUsers = computed(() =>
  props.detail.allUsers.filter(u => !props.detail.members.find(m => m.id === u.id))
)

const allInstances = computed(() => [
  ...props.detail.pgs.map(p => ({ value: `postgres|${p.id}`, label: `${p.name} (postgres)` })),
  ...props.detail.n8ns.map(n => ({ value: `n8n|${n.id}`, label: `${n.name} (n8n)` })),
])

const selectedUser = ref('')
const selectedInst = ref('')
const selectedLevel = ref('read')

async function addMember() {
  if (!selectedUser.value) return
  const res = await apiAddGroupMember(props.groupId, parseInt(selectedUser.value))
  if (res && res.ok) { toastStore.showToast('Membre ajouté'); selectedUser.value = ''; emit('reload') }
  else { const d = await res?.json().catch(() => ({})); toastStore.showToast(d.detail || 'Erreur', true) }
}

async function removeMember(userId) {
  const res = await apiRemoveGroupMember(props.groupId, userId)
  if (res && res.ok) { toastStore.showToast('Membre retiré'); emit('reload') }
  else toastStore.showToast('Erreur', true)
}

async function addPerm() {
  if (!selectedInst.value) return
  const [instType, instId] = selectedInst.value.split('|')
  const res = await apiAddGroupPermission(props.groupId, {
    instance_type: instType,
    instance_id: parseInt(instId),
    permission: selectedLevel.value,
  })
  if (res && res.ok) { toastStore.showToast('Permission ajoutée'); selectedInst.value = ''; emit('reload') }
  else { const d = await res?.json().catch(() => ({})); toastStore.showToast(d.detail || 'Erreur', true) }
}

async function removePerm(permId) {
  const res = await apiRemoveGroupPermission(props.groupId, permId)
  if (res && res.ok) { toastStore.showToast('Permission retirée'); emit('reload') }
  else toastStore.showToast('Erreur', true)
}
</script>
