<template>
  <div class="group-detail">
    <div class="group-detail-head">
      <h3 class="group-detail-title">{{ group.name }}</h3>
      <div class="instance-badge">
        <span class="badge" :class="`badge-type-${group.instance_type}`">{{ group.instance_type }}</span>
        <span style="font-size:13px;font-weight:500">{{ group.instance_name || '—' }}</span>
      </div>
    </div>

    <!-- Members -->
    <div class="group-detail-section">
      <div class="group-detail-section-title">Membres</div>

      <table v-if="detail.members.length" class="members-table">
        <thead>
          <tr>
            <th>Utilisateur</th>
            <th>Rôle</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in detail.members" :key="m.id">
            <td>
              <div style="font-weight:500;font-size:13px">{{ m.username }}</div>
              <div v-if="m.email" style="font-size:11px;color:#9CA3AF">{{ m.email }}</div>
            </td>
            <td>
              <span class="badge" :class="roleBadgeClass(m.role)">{{ m.role }}</span>
            </td>
            <td>
              <button class="btn btn-ghost btn-sm" @click="removeMember(m.id)">Retirer</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else style="font-size:12px;color:#9CA3AF;margin-bottom:10px">Aucun membre</div>

      <div v-if="availUsers.length" class="add-inline-form" style="margin-top:10px">
        <select v-model="selectedUser">
          <option value="" disabled>Choisir un utilisateur…</option>
          <option v-for="u in availUsers" :key="u.id" :value="u.id">{{ u.username }}</option>
        </select>
        <select v-model="selectedRole" style="width:140px">
          <option v-for="r in rolesForType" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
        <button class="btn btn-secondary btn-sm" @click="addMember" :disabled="!selectedUser">Ajouter</button>
      </div>
      <div v-else-if="detail.allUsers.length && !availUsers.length" style="font-size:12px;color:#9CA3AF;margin-top:6px">
        Tous les utilisateurs sont déjà membres
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useToastStore } from '../../stores/toast.js'
import { apiAddGroupMember, apiRemoveGroupMember } from '../../lib/api.js'

const ROLES = {
  postgres:   [{ value: 'admin', label: 'Admin' }, { value: 'read_write', label: 'Lecture/Écriture' }, { value: 'read_only', label: 'Lecture seule' }],
  mage:       [{ value: 'admin', label: 'Admin' }, { value: 'viewer', label: 'Viewer' }],
  metabase:   [{ value: 'admin', label: 'Admin' }, { value: 'viewer', label: 'Viewer' }],
  n8n:        [{ value: 'admin', label: 'Admin' }, { value: 'viewer', label: 'Viewer' }],
  airflow:    [{ value: 'admin', label: 'Admin' }, { value: 'viewer', label: 'Viewer' }],
  superset:   [{ value: 'admin', label: 'Admin' }, { value: 'viewer', label: 'Viewer' }],
  hasura:     [{ value: 'admin', label: 'Admin' }, { value: 'viewer', label: 'Viewer' }],
  ollama:     [{ value: 'admin', label: 'Admin' }, { value: 'viewer', label: 'Viewer' }],
  minio:      [{ value: 'admin', label: 'Admin' }, { value: 'read_write', label: 'Lecture/Écriture' }, { value: 'read_only', label: 'Lecture seule' }],
  redis:      [{ value: 'admin', label: 'Admin' }, { value: 'read_only', label: 'Lecture seule' }],
  postgrest:  [{ value: 'read_write', label: 'Lecture/Écriture' }, { value: 'read_only', label: 'Lecture seule' }],
  clickhouse: [{ value: 'admin', label: 'Admin' }, { value: 'viewer', label: 'Viewer' }],
  mariadb:    [{ value: 'admin', label: 'Admin' }, { value: 'viewer', label: 'Viewer' }],
  qdrant:     [{ value: 'admin', label: 'Admin' }, { value: 'viewer', label: 'Viewer' }],
}

const props = defineProps({
  group: Object,
  detail: Object,
})
const emit = defineEmits(['reload'])
const toastStore = useToastStore()

const rolesForType = computed(() => ROLES[props.group.instance_type] || [{ value: 'viewer', label: 'Viewer' }])

const availUsers = computed(() =>
  props.detail.allUsers.filter(u => !props.detail.members.find(m => m.id === u.id))
)

const selectedUser = ref('')
const selectedRole = ref(rolesForType.value[0]?.value || 'viewer')

function roleBadgeClass(role) {
  if (role === 'admin') return 'badge-admin'
  if (role === 'read_only' || role === 'viewer') return 'badge-user'
  return 'badge-secondary'
}

async function addMember() {
  if (!selectedUser.value) return
  const res = await apiAddGroupMember(props.group.id, parseInt(selectedUser.value), selectedRole.value)
  if (res && res.ok) {
    toastStore.showToast('Membre ajouté')
    selectedUser.value = ''
    selectedRole.value = rolesForType.value[0]?.value || 'viewer'
    emit('reload')
  } else {
    const d = await res?.json().catch(() => ({}))
    toastStore.showToast(d.detail || 'Erreur', true)
  }
}

async function removeMember(userId) {
  const res = await apiRemoveGroupMember(props.group.id, userId)
  if (res && res.ok) { toastStore.showToast('Membre retiré'); emit('reload') }
  else toastStore.showToast('Erreur', true)
}
</script>

<style scoped>
.instance-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--content-bg, #F9FAFB);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 7px 12px;
  margin-top: 6px;
}
.members-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-bottom: 4px;
}
.members-table th {
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: .4px;
  padding: 4px 8px 6px;
  border-bottom: 1px solid var(--border);
}
.members-table td {
  padding: 7px 8px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
.members-table tr:last-child td {
  border-bottom: none;
}
</style>
