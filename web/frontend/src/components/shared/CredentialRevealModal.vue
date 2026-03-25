<template>
  <BaseModal v-model="open" title="Identifiants de connexion">
    <div class="cred-warning">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style="flex-shrink:0;margin-top:1px">
        <path d="M8 1L1 14h14L8 1z" stroke="#D97706" stroke-width="1.3" fill="none"/>
        <path d="M8 6v4M8 11.5v.5" stroke="#D97706" stroke-width="1.4" stroke-linecap="round"/>
      </svg>
      <div>
        <strong>Affichage unique</strong>
        <p>Ces identifiants ne seront plus affichés. Notez-les maintenant ou retrouvez-les dans
          <strong>Sécurité &rarr; Identifiants</strong> (admin uniquement).</p>
      </div>
    </div>
    <div class="cred-list">
      <div v-for="(value, key) in credentials" :key="key" class="cred-row">
        <span class="cred-label">{{ labelFor(key) }}</span>
        <div class="cred-value-wrap">
          <code class="cred-value">{{ value }}</code>
          <button class="cred-copy" @click="copy(value)" :title="'Copier'">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.3"/>
              <path d="M3 11V3a1.5 1.5 0 011.5-1.5H11" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
    <div v-if="port" class="cred-row" style="margin-top:4px">
      <span class="cred-label">Port</span>
      <div class="cred-value-wrap">
        <code class="cred-value">{{ port }}</code>
        <button class="cred-copy" @click="copy(port)" :title="'Copier'">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.3"/>
            <path d="M3 11V3a1.5 1.5 0 011.5-1.5H11" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    </div>
    <div class="form-actions" style="margin-top:20px">
      <button class="btn btn-primary" @click="open = false">J'ai noté les identifiants</button>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue'
import BaseModal from './BaseModal.vue'
import { copyToClipboard } from '../../lib/utils.js'
import { useToastStore } from '../../stores/toast.js'

const props = defineProps({
  modelValue: Boolean,
  credentials: { type: Object, default: () => ({}) },
  port: { type: [Number, String], default: null },
})
const emit = defineEmits(['update:modelValue'])
const toastStore = useToastStore()

const open = ref(props.modelValue)
watch(() => props.modelValue, v => open.value = v)
watch(open, v => emit('update:modelValue', v))

const LABELS = {
  db_password: 'Mot de passe',
  db_user: 'Utilisateur',
  db_name: 'Base de données',
  password: 'Mot de passe',
  root_user: 'Utilisateur root',
  root_password: 'Mot de passe root',
  admin_password: 'Mot de passe admin',
  admin_user: 'Utilisateur admin',
  admin_secret: 'Secret administrateur',
}

function labelFor(key) {
  return LABELS[key] || key
}

async function copy(text) {
  try {
    await copyToClipboard(text)
    toastStore.showToast('Copié dans le presse-papiers')
  } catch {
    toastStore.showToast('Impossible de copier', true)
  }
}
</script>

<style scoped>
.cred-warning {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 18px;
  font-size: 13px;
  color: #92400E;
  line-height: 1.5;
}
.cred-warning p {
  margin: 2px 0 0;
}
.cred-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cred-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 8px 12px;
}
.cred-label {
  font-size: 13px;
  color: #6B7280;
  min-width: 130px;
}
.cred-value-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cred-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: #111827;
  user-select: all;
}
.cred-copy {
  background: none;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  padding: 3px 5px;
  cursor: pointer;
  color: #6B7280;
  display: flex;
  align-items: center;
}
.cred-copy:hover {
  background: #F3F4F6;
  color: #374151;
}
</style>
