<template>
  <BaseModal v-model="open" title="Nouvelle instance Hasura">
    <div class="form-group" style="margin-bottom:14px">
      <label>Nom de l'instance</label>
      <input type="text" v-model="form.name" placeholder="ex : graphql-api" style="width:100%">
    </div>
    <div class="form-group" style="margin-bottom:14px">
      <label>Base PostgreSQL <span style="color:#EF4444;font-weight:400">*</span></label>
      <select v-model="form.linked_pg_id" style="width:100%">
        <option value="">— Sélectionner une base —</option>
        <option v-for="pg in runningPgs" :key="pg.id" :value="pg.id">{{ pg.name }}</option>
      </select>
    </div>
    <div class="form-group" style="margin-bottom:6px">
      <label>Secret administrateur <span style="color:#EF4444;font-weight:400">*</span></label>
      <input type="text" v-model="form.admin_secret" placeholder="Secret pour l'accès à la console Hasura" style="width:100%">
    </div>
    <p style="font-size:12px;color:#9CA3AF;margin-bottom:20px">Hasura expose une API GraphQL sur la base PostgreSQL sélectionnée.</p>
    <div class="form-actions">
      <button class="btn btn-secondary" @click="open = false">Annuler</button>
      <button class="btn btn-primary" :disabled="loading" @click="submit">
        {{ loading ? 'Déploiement…' : "Créer l'instance" }}
      </button>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import BaseModal from '../shared/BaseModal.vue'
import { apiGetPostgres, apiCreateHasura } from '../../lib/api.js'
import { useToastStore } from '../../stores/toast.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'created'])

const toastStore = useToastStore()
const open = ref(props.modelValue)
watch(() => props.modelValue, v => open.value = v)
watch(open, v => emit('update:modelValue', v))

const form = reactive({ name: '', linked_pg_id: '', admin_secret: '' })
const loading = ref(false)
const allPgs = ref([])

const runningPgs = computed(() => allPgs.value.filter(p => p.status === 'running'))

watch(open, async (v) => {
  if (v) {
    const res = await apiGetPostgres()
    allPgs.value = res && res.ok ? await res.json() : []
  }
})

async function submit() {
  if (!form.name) {
    toastStore.showToast("Entrez un nom pour l'instance", true)
    return
  }
  if (!form.linked_pg_id) {
    toastStore.showToast('Sélectionnez une base PostgreSQL', true)
    return
  }
  if (!form.admin_secret) {
    toastStore.showToast('Le secret administrateur est requis', true)
    return
  }
  loading.value = true
  try {
    const body = {
      name: form.name,
      linked_pg_id: parseInt(form.linked_pg_id),
      admin_secret: form.admin_secret,
    }
    const res = await apiCreateHasura(body)
    if (res && res.ok) {
      open.value = false
      toastStore.showToast('Instance Hasura en cours de déploiement…')
      form.name = ''; form.linked_pg_id = ''; form.admin_secret = ''
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
