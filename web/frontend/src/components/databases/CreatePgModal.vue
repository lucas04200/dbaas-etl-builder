<template>
  <BaseModal v-model="open" title="Nouvelle instance PostgreSQL">
    <div class="form-grid-2" style="gap:14px">
      <div class="form-group">
        <label>Nom de l'instance</label>
        <input type="text" v-model="form.name" placeholder="ex : prod-analytics">
      </div>
      <div class="form-group">
        <label>Base par défaut</label>
        <input type="text" v-model="form.db_name" placeholder="ex : analytics_db">
      </div>
      <div class="form-group">
        <label>Utilisateur admin</label>
        <input type="text" v-model="form.db_user" placeholder="ex : admin">
      </div>
      <div class="form-group">
        <label>Mot de passe</label>
        <input type="password" v-model="form.db_password" placeholder="••••••••">
      </div>
    </div>
    <div class="form-actions">
      <button class="btn btn-secondary" @click="open = false">Annuler</button>
      <button class="btn btn-primary" :disabled="loading" @click="submit">
        {{ loading ? 'Déploiement…' : "Créer l'instance" }}
      </button>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import BaseModal from '../shared/BaseModal.vue'
import { apiCreatePostgres } from '../../lib/api.js'
import { useToastStore } from '../../stores/toast.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'created'])

const toastStore = useToastStore()

const open = ref(props.modelValue)
watch(() => props.modelValue, v => open.value = v)
watch(open, v => emit('update:modelValue', v))

const form = reactive({ name: '', db_name: '', db_user: '', db_password: '' })
const loading = ref(false)

async function submit() {
  if (!form.name || !form.db_name || !form.db_user || !form.db_password) {
    toastStore.showToast('Remplissez tous les champs', true)
    return
  }
  loading.value = true
  try {
    const res = await apiCreatePostgres({ ...form })
    if (res && res.ok) {
      open.value = false
      toastStore.showToast('Instance en cours de déploiement…')
      form.name = ''; form.db_name = ''; form.db_user = ''; form.db_password = ''
      emit('created')
    } else {
      const d = await res?.json().catch(() => ({}))
      toastStore.showToast(d.detail || 'Erreur', true)
    }
  } finally {
    loading.value = false
  }
}
</script>
