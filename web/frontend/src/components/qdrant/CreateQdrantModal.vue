<template>
  <BaseModal v-model="open" title="Nouvelle instance Qdrant">
    <div class="form-group" style="margin-bottom:14px">
      <label>Nom de l'instance</label>
      <input type="text" v-model="form.name" placeholder="ex : vecteurs-prod" style="width:100%">
    </div>
    <p style="font-size:12px;color:#9CA3AF;margin-bottom:20px">Qdrant sera accessible depuis le réseau Docker interne et sur localhost:port</p>
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
import { apiCreateQdrant } from '../../lib/api.js'
import { useToastStore } from '../../stores/toast.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'created'])

const toastStore = useToastStore()
const open = ref(props.modelValue)
watch(() => props.modelValue, v => open.value = v)
watch(open, v => emit('update:modelValue', v))

const form = reactive({ name: '' })
const loading = ref(false)

async function submit() {
  if (!form.name) {
    toastStore.showToast("Entrez un nom pour l'instance", true)
    return
  }
  loading.value = true
  try {
    const res = await apiCreateQdrant({ name: form.name })
    if (res && res.ok) {
      open.value = false
      toastStore.showToast('Instance Qdrant en cours de déploiement…')
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
