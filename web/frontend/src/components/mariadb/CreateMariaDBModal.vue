<template>
  <BaseModal v-model="open" title="Nouvelle instance MariaDB">
    <div class="form-group" style="margin-bottom:14px">
      <label>Nom de l'instance</label>
      <input type="text" v-model="form.name" placeholder="ex : db-prod" style="width:100%">
    </div>
    <div class="form-group" style="margin-bottom:14px">
      <label>Mot de passe root <span style="color:#EF4444;font-weight:400">*</span></label>
      <input type="text" v-model="form.root_password" placeholder="Mot de passe du compte root" style="width:100%">
    </div>
    <div class="form-group" style="margin-bottom:6px">
      <label>Nom de la base <span style="color:#9CA3AF;font-weight:400">(optionnel)</span></label>
      <input type="text" v-model="form.db_name" placeholder="Laisser vide = même que le nom de l'instance" style="width:100%">
    </div>
    <p style="font-size:12px;color:#9CA3AF;margin-bottom:20px">MariaDB sera accessible depuis le réseau Docker interne et sur localhost:port</p>
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
import { apiCreateMariaDB } from '../../lib/api.js'
import { useToastStore } from '../../stores/toast.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'created'])

const toastStore = useToastStore()
const open = ref(props.modelValue)
watch(() => props.modelValue, v => open.value = v)
watch(open, v => emit('update:modelValue', v))

const form = reactive({ name: '', root_password: '', db_name: '' })
const loading = ref(false)

async function submit() {
  if (!form.name) {
    toastStore.showToast("Entrez un nom pour l'instance", true)
    return
  }
  if (!form.root_password) {
    toastStore.showToast('Le mot de passe root est requis', true)
    return
  }
  loading.value = true
  try {
    const body = {
      name: form.name,
      root_password: form.root_password,
      db_name: form.db_name || '',
    }
    const res = await apiCreateMariaDB(body)
    if (res && res.ok) {
      open.value = false
      toastStore.showToast('Instance MariaDB en cours de déploiement…')
      form.name = ''; form.root_password = ''; form.db_name = ''
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
