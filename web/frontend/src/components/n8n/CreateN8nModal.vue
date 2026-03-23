<template>
  <BaseModal v-model="open" title="Nouvelle instance n8n">
    <div class="form-group" style="margin-bottom:14px">
      <label>Nom de l'instance</label>
      <input type="text" v-model="form.name" placeholder="ex : workflow-prod" style="width:100%">
    </div>
    <div class="form-group" style="margin-bottom:6px">
      <label>Base PostgreSQL liée <span style="color:#9CA3AF;font-weight:400">(optionnel)</span></label>
      <select v-model="form.linked_pg_id" style="width:100%">
        <option value="">— Aucune (SQLite local) —</option>
        <option v-for="pg in runningPgs" :key="pg.id" :value="pg.id">{{ pg.name }}</option>
      </select>
    </div>
    <p style="font-size:12px;color:#9CA3AF;margin-bottom:20px">Si une base est liée, n8n stocke ses workflows dans PostgreSQL.</p>
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
import { apiGetPostgres, apiCreateN8n } from '../../lib/api.js'
import { useToastStore } from '../../stores/toast.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'created'])

const toastStore = useToastStore()
const open = ref(props.modelValue)
watch(() => props.modelValue, v => open.value = v)
watch(open, v => emit('update:modelValue', v))

const form = reactive({ name: '', linked_pg_id: '' })
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
  loading.value = true
  try {
    const body = {
      name: form.name,
      linked_pg_id: form.linked_pg_id ? parseInt(form.linked_pg_id) : null,
    }
    const res = await apiCreateN8n(body)
    if (res && res.ok) {
      open.value = false
      toastStore.showToast('Instance n8n en cours de déploiement…')
      form.name = ''; form.linked_pg_id = ''
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
