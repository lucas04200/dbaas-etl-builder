<template>
  <BaseModal v-model="open" title="Nouvelle instance Redis">
    <div class="form-group" style="margin-bottom:14px">
      <label>Nom de l'instance</label>
      <input type="text" v-model="form.name" placeholder="ex : cache-prod" style="width:100%">
    </div>
    <div class="form-group" style="margin-bottom:6px">
      <label>Mot de passe <span style="color:#9CA3AF;font-weight:400">(optionnel)</span></label>
      <input type="text" v-model="form.password" placeholder="Laisser vide = sans authentification" style="width:100%">
    </div>
    <p style="font-size:12px;color:#9CA3AF;margin-bottom:20px">Redis sera accessible depuis le réseau Docker interne et sur localhost:port</p>
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
import { apiCreateRedis } from '../../lib/api.js'
import { useToastStore } from '../../stores/toast.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'created'])

const toastStore = useToastStore()
const open = ref(props.modelValue)
watch(() => props.modelValue, v => open.value = v)
watch(open, v => emit('update:modelValue', v))

const form = reactive({ name: '', password: '' })
const loading = ref(false)

async function submit() {
  if (!form.name) {
    toastStore.showToast("Entrez un nom pour l'instance", true)
    return
  }
  loading.value = true
  try {
    const body = {
      name: form.name,
      password: form.password || null,
    }
    const res = await apiCreateRedis(body)
    if (res && res.ok) {
      open.value = false
      toastStore.showToast('Instance Redis en cours de déploiement…')
      form.name = ''; form.password = ''
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
