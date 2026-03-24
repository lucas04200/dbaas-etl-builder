<template>
  <div class="overlay" @click.self="$emit('cancel')">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title">Nouveau lien</div>
        <div class="modal-sub">{{ source }} → {{ target }}</div>
      </div>
      <div class="modal-body">
        <label class="field-label">Label du lien <span class="optional">optionnel</span></label>
        <input
          ref="inputEl"
          v-model="label"
          class="field-input"
          placeholder="ex : données clients, pipeline ETL…"
          @keydown.enter="confirm"
          @keydown.escape="$emit('cancel')"
        />
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" @click="$emit('cancel')">Annuler</button>
        <button class="btn btn-primary" @click="confirm">Créer le lien</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  source: { type: String, required: true },
  target: { type: String, required: true },
})
const emit = defineEmits(['confirm', 'cancel'])

const label = ref('')
const inputEl = ref(null)

function confirm() {
  emit('confirm', label.value.trim())
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
  width: 380px; max-width: 95vw;
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

.modal-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 14px 20px; border-top: 1px solid var(--border);
}
</style>
