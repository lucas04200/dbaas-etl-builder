<template>
  <BaseModal v-model="open" title="Nouvelle instance PostgreSQL">
    <div class="form-grid-2" style="gap:14px">
      <div class="form-group">
        <label>Nom de l'instance</label>
        <input type="text" v-model="form.name" placeholder="ex : prod-analytics">
      </div>
      <div class="form-group">
        <label>Base par défaut <span style="color:#9CA3AF;font-weight:400">(optionnel)</span></label>
        <input type="text" v-model="form.db_name" placeholder="Par défaut = nom de l'instance">
      </div>
      <div class="form-group">
        <label>Utilisateur admin <span style="color:#9CA3AF;font-weight:400">(optionnel)</span></label>
        <input type="text" v-model="form.db_user" placeholder="Par défaut = admin">
      </div>
    </div>
    <p style="font-size:12px;color:#9CA3AF;margin:10px 0 16px">Le mot de passe sera généré automatiquement et affiché une seule fois après la création.</p>
    <div class="form-actions">
      <button class="btn btn-secondary" @click="open = false">Annuler</button>
      <button class="btn btn-primary" :disabled="loading" @click="submit">
        {{ loading ? 'Déploiement…' : "Créer l'instance" }}
      </button>
    </div>
  </BaseModal>

  <CredentialRevealModal v-model="showCreds" :credentials="creds" :port="credsPort" />
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import BaseModal from '../shared/BaseModal.vue'
import CredentialRevealModal from '../shared/CredentialRevealModal.vue'
import { apiCreatePostgres } from '../../lib/api.js'
import { useToastStore } from '../../stores/toast.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'created'])

const toastStore = useToastStore()

const open = ref(props.modelValue)
watch(() => props.modelValue, v => open.value = v)
watch(open, v => emit('update:modelValue', v))

const form = reactive({ name: '', db_name: '', db_user: '' })
const loading = ref(false)
const showCreds = ref(false)
const creds = ref({})
const credsPort = ref(null)

async function submit() {
  if (!form.name) {
    toastStore.showToast('Entrez un nom pour l\'instance', true)
    return
  }
  loading.value = true
  try {
    const res = await apiCreatePostgres({ name: form.name, db_name: form.db_name, db_user: form.db_user })
    if (res && res.ok) {
      const data = await res.json()
      open.value = false
      toastStore.showToast('Instance en cours de déploiement…')
      creds.value = data.credentials || {}
      credsPort.value = data.port
      showCreds.value = true
      form.name = ''; form.db_name = ''; form.db_user = ''
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
