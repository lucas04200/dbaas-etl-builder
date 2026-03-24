<template>
  <div class="overlay" @click.self="$emit('cancel')">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title">{{ isManual ? 'Modifier le lien' : 'Lien détecté automatiquement' }}</div>
        <div class="modal-sub">{{ source }} → {{ target }}</div>
      </div>
      <div class="modal-body">
        <label class="field-label">
          Label du lien
          <span class="optional">{{ isManual ? 'optionnel' : 'lecture seule' }}</span>
        </label>
        <input
          ref="inputEl"
          v-model="label"
          class="field-input"
          :disabled="!isManual"
          placeholder="ex : données clients, pipeline ETL…"
          @keydown.enter="isManual && save()"
          @keydown.escape="$emit('cancel')"
        />
        <div v-if="!isManual" class="auto-notice">
          Ce lien est détecté automatiquement depuis la configuration du service. Il ne peut pas être modifié manuellement.
        </div>
      </div>
      <div class="modal-footer">
        <button v-if="isManual" class="btn btn-danger" @click="$emit('delete')">Supprimer</button>
        <div style="flex:1" />
        <button class="btn btn-ghost" @click="$emit('cancel')">Fermer</button>
        <button v-if="isManual" class="btn btn-primary" @click="save">Enregistrer</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  source: { type: String, required: true },
  target: { type: String, required: true },
  currentLabel: { type: String, default: '' },
  isManual: { type: Boolean, default: false },
})
const emit = defineEmits(['save', 'delete', 'cancel'])

const label = ref(props.currentLabel)
const inputEl = ref(null)

function save() {
  emit('save', label.value.trim())
}

onMounted(() => inputEl.value?.focus())
</script>

<style scoped>
.overlay {
  position: fixed; inset: 0; z-index: 2000;
  background: rgba(0,0,0,0.3);
  display: flex; align-items: center; justify-content: center;
}
.modal {
  background: var(--white);
  border-radius: 12px;
  width: 400px; max-width: 95vw;
  box-shadow: 0 16px 48px rgba(0,0,0,0.14);
  overflow: hidden;
}
.modal-header {
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--border);
}
.modal-title { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.modal-sub { font-size: 12px; color: var(--text-muted); margin-top: 3px; font-family: monospace; }

.modal-body { padding: 18px 20px; }
.field-label {
  display: block; font-size: 12px; font-weight: 600;
  color: var(--text-secondary); margin-bottom: 7px;
}
.optional {
  font-weight: 400; color: var(--text-muted); margin-left: 4px;
}
.field-input {
  width: 100%; box-sizing: border-box;
  border: 1.5px solid var(--border); border-radius: 8px;
  padding: 8px 12px; font-size: 13.5px; font-family: inherit;
  color: var(--text-primary); background: var(--white); outline: none;
}
.field-input:focus { border-color: var(--accent); }
.field-input:disabled { background: var(--content-bg); color: var(--text-muted); cursor: not-allowed; }

.auto-notice {
  margin-top: 10px; font-size: 12px; color: var(--text-muted);
  background: #F9FAFB; border-radius: 6px; padding: 8px 10px;
  border: 1px solid var(--border);
}

.modal-footer {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 20px; border-top: 1px solid var(--border);
}

.btn-danger {
  background: #FEF2F2; color: #DC2626;
  border: 1.5px solid #FECACA;
  font-size: 12.5px; font-weight: 600;
  padding: 6px 14px; border-radius: 7px; cursor: pointer;
  transition: background 0.15s;
}
.btn-danger:hover { background: #FEE2E2; }
</style>
