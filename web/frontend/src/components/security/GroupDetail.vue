<template>
  <div>
    <div class="accordion-section">
      <div class="accordion-section-title">Membres</div>
      <div class="pill-list">
        <span v-if="!detail.members.length" style="font-size:12px;color:#9CA3AF">Aucun membre</span>
        <span v-for="m in detail.members" :key="m.id" class="pill">
          {{ m.username }}
          <button class="pill-remove" @click="removeMember(m.id)">×</button>
        </span>
      </div>
      <div v-if="availUsers.length" class="add-inline-form" style="margin-top:10px">
        <select v-model="selectedUser">
          <option v-for="u in availUsers" :key="u.id" :value="u.id">{{ u.username }}</option>
        </select>
        <button class="btn btn-secondary btn-sm" @click="addMember">Ajouter</button>
      </div>
    </div>

    <div class="accordion-section">
      <div class="accordion-section-title">Permissions</div>
      <div class="pill-list">
        <span v-if="!detail.perms.length" style="font-size:12px;color:#9CA3AF">Aucune permission</span>
        <span v-for="p in detail.perms" :key="p.id" :class="['pill', 'pill-perm', p.permission]">
          {{ p.instance_name }} · {{ p.permission }}
          <button class="pill-remove" @click="removePerm(p.id)">×</button>
        </span>
      </div>
      <div v-if="allInstances.length" class="add-inline-form" style="margin-top:10px">
        <select v-model="selectedInst">
          <option v-for="inst in allInstances" :key="inst.value" :value="inst.value">{{ inst.label }}</option>
        </select>
        <select v-model="selectedLevel" style="width:100px">
          <option value="read">Lecture</option>
          <option value="write">Écriture</option>
          <option value="admin">Admin</option>
        </select>
        <button class="btn btn-secondary btn-sm" @click="addPerm">Ajouter</button>
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
  detail: Object,
})
const emit = defineEmits(['reload'])
const toastStore = useToastStore()

const availUsers = computed(() =>
  props.detail.allUsers.filter(u => !props.detail.members.find(m => m.id === u.id))
)

const allInstances = computed(() => {
  const pgOpts = props.detail.pgs.map(p => ({ value: `postgres|${p.id}`, label: `${p.name} (postgres)` }))
  const n8nOpts = props.detail.n8ns.map(n => ({ value: `n8n|${n.id}`, label: `${n.name} (n8n)` }))
  return [...pgOpts, ...n8nOpts]
})

const selectedUser = ref(availUsers.value[0]?.id || null)
const selectedInst = ref(allInstances.value[0]?.value || '')
const selectedLevel = ref('read')

async function addMember() {
  if (!selectedUser.value) return
  const res = await apiAddGroupMember(props.groupId, parseInt(selectedUser.value))
  if (res && res.ok) { toastStore.showToast('Membre ajouté'); emit('reload') }
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
  if (res && res.ok) { toastStore.showToast('Permission ajoutée'); emit('reload') }
  else { const d = await res?.json().catch(() => ({})); toastStore.showToast(d.detail || 'Erreur', true) }
}

async function removePerm(permId) {
  const res = await apiRemoveGroupPermission(props.groupId, permId)
  if (res && res.ok) { toastStore.showToast('Permission retirée'); emit('reload') }
  else toastStore.showToast('Erreur', true)
}
</script>
