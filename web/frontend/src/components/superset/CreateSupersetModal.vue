<template>
  <BaseModal v-model="open" title="Nouvelle instance Superset">
    <div class="form-group" style="margin-bottom:14px">
      <label>Nom de l'instance</label>
      <input type="text" v-model="form.name" placeholder="ex : bi-prod" style="width:100%">
    </div>
    <div class="internal-db-info">
      <svg width="14" height="14" viewBox="0 0 15 15" fill="none" style="flex-shrink:0;margin-top:1px">
        <circle cx="7.5" cy="7.5" r="6" stroke="#4C6EF5" stroke-width="1.3"/>
        <path d="M7.5 5v3M7.5 10v.5" stroke="#4C6EF5" stroke-width="1.4" stroke-linecap="round"/>
      </svg>
      <p>Une base PostgreSQL dédiée sera automatiquement créée. Le mot de passe admin sera généré et affiché une seule fois.</p>
    </div>
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
import { apiCreateSuperset } from '../../lib/api.js'
import { useToastStore } from '../../stores/toast.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'created'])

const toastStore = useToastStore()
const open = ref(props.modelValue)
watch(() => props.modelValue, v => open.value = v)
watch(open, v => emit('update:modelValue', v))

const form = reactive({ name: '' })
const loading = ref(false)
const showCreds = ref(false)
const creds = ref({})
const credsPort = ref(null)

async function submit() {
  if (!form.name) {
    toastStore.showToast("Entrez un nom pour l'instance", true)
    return
  }
  loading.value = true
  try {
    const res = await apiCreateSuperset({ name: form.name })
    if (res && res.ok) {
      const data = await res.json()
      open.value = false
      toastStore.showToast('Instance Superset en cours de déploiement…')
      creds.value = data.credentials || {}
      credsPort.value = data.port
      showCreds.value = true
      form.name = ''
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

<style scoped>
.internal-db-info {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  background: #EEF2FF;
  border: 1px solid #C7D2FE;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 20px;
  font-size: 12.5px;
  color: #3730A3;
  line-height: 1.5;
}
</style>
