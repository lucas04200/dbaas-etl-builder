<template>
  <div>
    <div class="card">
      <div class="card-title">Utilisateurs</div>
      <div v-if="loading" class="empty">Chargement…</div>
      <div v-else-if="!users.length" class="empty">Aucun utilisateur</div>
      <table v-else>
        <thead>
          <tr>
            <th>Utilisateur</th>
            <th>Rôle</th>
            <th>Créé le</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>
              <strong>{{ u.username }}</strong>
              <div v-if="u.email" style="font-size:12px;color:#9CA3AF">{{ u.email }}</div>
            </td>
            <td>
              <span :class="['badge', 'badge-' + u.role]">
                {{ u.role === 'admin' ? 'Admin' : 'Utilisateur' }}
              </span>
            </td>
            <td style="color:#9CA3AF">{{ fmtDate(u.created_at) }}</td>
            <td style="text-align:right">
              <button v-if="u.id !== currentUser?.id" class="btn btn-ghost btn-sm" @click="deleteUser(u)">Supprimer</button>
              <span v-else style="font-size:12px;color:#9CA3AF">Vous</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import { useToastStore } from '../../stores/toast.js'
import { apiGetUsers, apiDeleteUser } from '../../lib/api.js'

const authStore = useAuthStore()
const toastStore = useToastStore()

const currentUser = computed(() => authStore.currentUser)
const users = ref([])
const loading = ref(true)

function fmtDate(s) {
  if (!s) return '—'
  try {
    return new Date(s.replace(' ', 'T')).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch { return s }
}

async function loadUsers() {
  const res = await apiGetUsers()
  if (!res || !res.ok) { loading.value = false; return }
  users.value = await res.json()
  loading.value = false
}

async function deleteUser(u) {
  if (!confirm(`Supprimer « ${u.username} » ?`)) return
  const res = await apiDeleteUser(u.id)
  if (res && res.ok) {
    toastStore.showToast('Utilisateur supprimé')
    await loadUsers()
  } else {
    toastStore.showToast('Erreur', true)
  }
}

onMounted(loadUsers)
</script>
