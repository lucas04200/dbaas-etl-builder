<template>
  <BaseModal v-model="open" title="Nouvelle instance MinIO">
    <div class="form-group" style="margin-bottom:14px">
      <label>Nom de l'instance</label>
      <input type="text" v-model="form.name" placeholder="ex : storage-prod" style="width:100%">
    </div>
    <div class="form-group" style="margin-bottom:14px">
      <label>Utilisateur root</label>
      <input type="text" v-model="form.root_user" placeholder="minioadmin" style="width:100%">
    </div>
    <div class="form-group" style="margin-bottom:6px">
      <label>Mot de passe root <span style="color:#EF4444;font-weight:400">*</span></label>
      <input type="password" v-model="form.root_password" placeholder="Minimum 8 caractères" style="width:100%">
    </div>
    <p style="font-size:12px;color:#9CA3AF;margin-bottom:20px">MinIO fournit un stockage objet S3-compatible. L'interface de gestion est accessible sur le port console.</p>
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
import { apiCreateMinIO } from '../../lib/api.js'
import { useToastStore } from '../../stores/toast.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'created'])

const toastStore = useToastStore()
const open = ref(props.modelValue)
watch(() => props.modelValue, v => open.value = v)
watch(open, v => emit('update:modelValue', v))

const form = reactive({ name: '', root_user: 'minioadmin', root_password: '' })
const loading = ref(false)

async function submit() {
  if (!form.name) {
    toastStore.showToast("Entrez un nom pour l'instance", true)
    return
  }
  if (!form.root_password || form.root_password.length < 8) {
    toastStore.showToast('Le mot de passe doit contenir au moins 8 caractères', true)
    return
  }
  loading.value = true
  try {
    const body = {
      name: form.name,
      root_user: form.root_user || 'minioadmin',
      root_password: form.root_password,
    }
    const res = await apiCreateMinIO(body)
    if (res && res.ok) {
      open.value = false
      toastStore.showToast('Instance MinIO en cours de déploiement…')
      form.name = ''; form.root_user = 'minioadmin'; form.root_password = ''
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
