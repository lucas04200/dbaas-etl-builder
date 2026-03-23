<template>
  <div class="ollama-card" :class="{ 'is-running': instance.status === 'running' }">
    <!-- Header -->
    <div class="ollama-card-head">
      <div class="ollama-card-title">
        <div class="ollama-icon">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="7" stroke="#111827" stroke-width="1.4"/>
            <circle cx="7.5" cy="9" r="1.5" fill="#111827"/>
            <circle cx="12.5" cy="9" r="1.5" fill="#111827"/>
            <path d="M7 13c1 1 6 1 6 0" stroke="#111827" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
        </div>
        <div>
          <div class="ollama-name">{{ instance.name }}</div>
          <div class="ollama-meta">
            <code>http://localhost:{{ instance.host_port }}</code>
          </div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px">
        <span :class="['badge', 'badge-' + instance.status]">{{ statusLabel(instance.status) }}</span>
        <button v-if="isAdmin" class="btn btn-ghost btn-sm" @click="$emit('delete', instance)">Supprimer</button>
      </div>
    </div>

    <!-- Model management (only when running) -->
    <template v-if="instance.status === 'running'">
      <!-- Installed models -->
      <div class="ollama-section-label">
        Modèles installés
        <span class="count-badge">{{ models.length }}</span>
        <button class="refresh-btn" @click="loadModels" title="Actualiser">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" :class="{ spin: loadingModels }">
            <path d="M10.5 6a4.5 4.5 0 1 1-1.2-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            <path d="M10.5 2v3h-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>

      <div v-if="loadingModels" class="ollama-loading">Chargement des modèles…</div>
      <div v-else-if="!models.length" class="ollama-empty">
        Aucun modèle installé. Téléchargez-en un ci-dessous.
      </div>
      <div v-else class="model-list">
        <div v-for="m in models" :key="m.name" class="model-row">
          <div class="model-info">
            <span class="model-name">{{ m.name }}</span>
            <span class="model-size">{{ formatSize(m.size) }}</span>
            <span v-if="m.details?.family" class="model-family">{{ m.details.family }}</span>
          </div>
          <div class="model-actions">
            <button class="btn btn-sm btn-secondary" @click="openChat(m.name)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M1 2.5h10v6a1 1 0 01-1 1H2a1 1 0 01-1-1v-6z" stroke="currentColor" stroke-width="1.2"/>
                <path d="M3.5 9.5L2 11.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
              </svg>
              Tester
            </button>
            <button v-if="isAdmin" class="btn btn-sm btn-ghost" @click="deleteModel(m.name)" title="Supprimer ce modèle">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2 3h8M5 3V1.5h2V3M4.5 5v4M7.5 5v4M3 3l.5 7h5l.5-7" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Pull model -->
      <div class="ollama-section-label" style="margin-top:16px">Ajouter un modèle</div>
      <div class="pull-row">
        <input
          v-model="pullName"
          class="pull-input"
          placeholder="ex : llama3.2:3b"
          @keydown.enter="pullModel"
        />
        <button class="btn btn-primary btn-sm" :disabled="!pullName.trim() || isPulling" @click="pullModel">
          <svg v-if="isPulling" width="12" height="12" viewBox="0 0 12 12" fill="none" class="spin">
            <circle cx="6" cy="6" r="4.5" stroke="currentColor" stroke-width="1.5" stroke-dasharray="14" stroke-dashoffset="5"/>
          </svg>
          {{ isPulling ? 'Téléchargement…' : 'Télécharger' }}
        </button>
      </div>

      <!-- Suggested models -->
      <div class="suggestions">
        <span class="sug-label">Suggestions :</span>
        <button
          v-for="s in SUGGESTED"
          :key="s.name"
          class="sug-btn"
          :title="s.desc"
          @click="pullName = s.name"
        >{{ s.name }}</button>
      </div>

      <!-- Integration info -->
      <div class="integration-block">
        <div class="integration-title">Utilisation de l'API</div>
        <code class="integration-code">curl http://localhost:{{ instance.host_port }}/api/generate \
  -d '{"model":"llama3.2:3b","prompt":"Bonjour","stream":false}'</code>
        <div class="integration-title" style="margin-top:8px">Compatible OpenAI SDK</div>
        <code class="integration-code">from openai import OpenAI
client = OpenAI(base_url="http://localhost:{{ instance.host_port }}/v1", api_key="ollama")
r = client.chat.completions.create(model="llama3.2:3b", messages=[...])</code>
      </div>
    </template>

    <!-- Chat modal -->
    <OllamaChat
      v-if="chatOpen"
      :instance-id="instance.id"
      :model="chatModel"
      @close="chatOpen = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import { useToastStore } from '../../stores/toast.js'
import {
  apiOllamaListModels, apiOllamaPullModel, apiOllamaPullStatus, apiOllamaDeleteModel,
} from '../../lib/api.js'
import OllamaChat from './OllamaChat.vue'

const props = defineProps({ instance: Object })
defineEmits(['delete'])

const authStore = useAuthStore()
const toastStore = useToastStore()
const isAdmin = computed(() => authStore.currentUser?.role === 'admin')

const models = ref([])
const loadingModels = ref(false)
const pullName = ref('')
const isPulling = ref(false)
const chatOpen = ref(false)
const chatModel = ref('')
let pullPollTimer = null

const SUGGESTED = [
  { name: 'llama3.2:3b',   desc: 'Llama 3.2 3B — léger et rapide' },
  { name: 'llama3.1:8b',   desc: 'Llama 3.1 8B — bon équilibre qualité/vitesse' },
  { name: 'mistral:7b',    desc: 'Mistral 7B — excellent en français' },
  { name: 'phi3:mini',     desc: 'Phi-3 Mini (Microsoft) — très léger' },
  { name: 'gemma2:2b',     desc: 'Gemma 2 2B (Google) — ultra léger' },
  { name: 'nomic-embed-text', desc: 'Embeddings pour Qdrant/pgvector' },
  { name: 'codellama:7b',  desc: 'Code Llama — génération de code' },
]

function statusLabel(s) {
  return { running: 'Actif', provisioning: 'Déploiement…', error: 'Erreur', stopped: 'Arrêté' }[s] || s
}

function formatSize(bytes) {
  if (!bytes) return ''
  const gb = bytes / 1e9
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / 1e6).toFixed(0)} MB`
}

async function loadModels() {
  if (props.instance.status !== 'running') return
  loadingModels.value = true
  const res = await apiOllamaListModels(props.instance.id)
  if (res && res.ok) {
    const data = await res.json()
    models.value = data.models || []
  }
  loadingModels.value = false
}

async function pullModel() {
  const name = pullName.value.trim()
  if (!name) return
  isPulling.value = true
  const res = await apiOllamaPullModel(props.instance.id, name)
  if (!res || !res.ok) {
    toastStore.showToast('Erreur lors du lancement du téléchargement', true)
    isPulling.value = false
    return
  }
  toastStore.showToast(`Téléchargement de ${name} lancé…`)
  startPullPoll(name)
}

function startPullPoll(modelName) {
  if (pullPollTimer) return
  pullPollTimer = setInterval(async () => {
    const res = await apiOllamaPullStatus(props.instance.id)
    if (!res || !res.ok) return
    const status = await res.json()
    const s = status[modelName]
    if (s === 'done') {
      isPulling.value = false
      pullName.value = ''
      toastStore.showToast(`Modèle ${modelName} installé !`)
      clearInterval(pullPollTimer); pullPollTimer = null
      loadModels()
    } else if (s === 'error') {
      isPulling.value = false
      toastStore.showToast(`Erreur lors du téléchargement de ${modelName}`, true)
      clearInterval(pullPollTimer); pullPollTimer = null
    }
  }, 3000)
}

async function deleteModel(name) {
  if (!confirm(`Supprimer le modèle « ${name} » ?`)) return
  const res = await apiOllamaDeleteModel(props.instance.id, name)
  if (res && res.ok) {
    toastStore.showToast(`Modèle ${name} supprimé`)
    loadModels()
  } else {
    toastStore.showToast('Erreur lors de la suppression', true)
  }
}

function openChat(model) {
  chatModel.value = model
  chatOpen.value = true
}

onMounted(() => {
  if (props.instance.status === 'running') loadModels()
})

onUnmounted(() => {
  if (pullPollTimer) clearInterval(pullPollTimer)
})
</script>

<style scoped>
.ollama-card {
  background: var(--white);
  border: 1.5px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.ollama-card.is-running { border-color: var(--accent); }

.ollama-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}
.ollama-card-title { display: flex; align-items: center; gap: 12px; }
.ollama-icon {
  width: 38px; height: 38px; border-radius: 9px;
  background: #F9FAFB; border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.ollama-name { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.ollama-meta code { font-size: 11.5px; color: #6B7280; }

.ollama-section-label {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.7px; color: var(--text-muted);
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 8px; margin-top: 4px;
}
.count-badge {
  background: #F3F4F6; color: #6B7280;
  font-size: 10px; padding: 0 6px; border-radius: 10px;
}
.refresh-btn {
  background: none; border: none; cursor: pointer; color: var(--text-muted);
  padding: 2px; display: flex; align-items: center;
}
.refresh-btn:hover { color: var(--accent); }

.ollama-loading, .ollama-empty {
  font-size: 13px; color: #9CA3AF; padding: 8px 0;
}

.model-list { display: flex; flex-direction: column; gap: 4px; }
.model-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 10px; border-radius: 8px; background: var(--content-bg);
  border: 1px solid var(--border);
}
.model-info { display: flex; align-items: center; gap: 10px; min-width: 0; }
.model-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.model-size { font-size: 11.5px; color: #9CA3AF; }
.model-family {
  font-size: 10px; padding: 1px 6px; border-radius: 10px;
  background: #EFF6FF; color: #3B82F6; font-weight: 600;
}
.model-actions { display: flex; gap: 5px; flex-shrink: 0; }

.pull-row { display: flex; gap: 8px; }
.pull-input {
  flex: 1; border: 1.5px solid var(--border); border-radius: 8px;
  padding: 7px 11px; font-size: 13px; font-family: inherit;
  background: var(--white); color: var(--text-primary); outline: none;
}
.pull-input:focus { border-color: var(--accent); }

.suggestions { display: flex; align-items: center; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
.sug-label { font-size: 11.5px; color: var(--text-muted); }
.sug-btn {
  font-size: 11.5px; padding: 2px 9px; border-radius: 20px;
  border: 1.5px solid var(--border); background: var(--white);
  color: var(--text-secondary); cursor: pointer; font-family: inherit;
  transition: all 0.1s;
}
.sug-btn:hover { border-color: var(--accent); color: var(--accent); }

.integration-block {
  margin-top: 16px;
  background: #F8FAFC; border: 1px solid var(--border);
  border-radius: 8px; padding: 12px 14px;
}
.integration-title {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 6px;
}
.integration-code {
  display: block;
  font-size: 11.5px; color: #374151;
  font-family: 'SF Mono', 'Fira Mono', monospace;
  white-space: pre-wrap; word-break: break-all;
  line-height: 1.6;
}

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
