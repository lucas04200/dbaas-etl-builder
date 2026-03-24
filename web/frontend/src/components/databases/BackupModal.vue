<template>
  <div class="backup-overlay" @click.self="$emit('close')">
    <div class="backup-panel">
      <div class="backup-header">
        <div>
          <div class="backup-title">Sauvegardes — <span style="color:var(--accent)">{{ instance.name }}</span></div>
          <div class="backup-sub">pg_dump · format custom (pg_restore compatible)</div>
        </div>
        <button class="close-btn" @click="$emit('close')">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </button>
      </div>

      <!-- New backup -->
      <div class="new-backup-row">
        <input v-model="database" class="db-input" placeholder="Nom de la base (ex: postgres)" />
        <button class="btn btn-primary" :disabled="backing || !database.trim()" @click="doBackup">
          <svg v-if="backing" width="12" height="12" viewBox="0 0 12 12" fill="none" class="spin">
            <circle cx="6" cy="6" r="4.5" stroke="currentColor" stroke-width="1.5" stroke-dasharray="14" stroke-dashoffset="5"/>
          </svg>
          <svg v-else width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 2v6M3 6l3 3 3-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M1 10h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          {{ backing ? 'Sauvegarde…' : 'Sauvegarder' }}
        </button>
      </div>

      <!-- Backup list -->
      <div class="backup-section-label">
        Sauvegardes disponibles
        <span class="count">{{ backups.length }}</span>
      </div>

      <div v-if="loadingList" class="backup-loading">Chargement…</div>
      <div v-else-if="!backups.length" class="backup-empty">Aucune sauvegarde. Lancez-en une ci-dessus.</div>
      <div v-else class="backup-list">
        <div v-for="b in backups" :key="b.filename" class="backup-row">
          <div class="backup-info">
            <span class="backup-file">{{ b.filename }}</span>
            <span class="backup-meta">{{ formatSize(b.size) }} · {{ formatDate(b.created_at) }}</span>
          </div>
          <div class="backup-actions">
            <a class="btn btn-sm btn-secondary" :href="downloadUrl(b.filename)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M6 2v6M3 6l3 3 3-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M1 10h10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              </svg>
              Télécharger
            </a>
            <button class="btn btn-sm btn-ghost" @click="deleteBackup(b.filename)">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2 3h8M5 3V1.5h2V3M4.5 5v4M7.5 5v4M3 3l.5 7h5l.5-7" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useToastStore } from '../../stores/toast.js'
import { apiPgBackup, apiPgListBackups, apiPgDeleteBackup } from '../../lib/api.js'

const props = defineProps({ instance: { type: Object, required: true } })
defineEmits(['close'])

const toastStore = useToastStore()
const database = ref(props.instance.db_name || 'postgres')
const backups = ref([])
const backing = ref(false)
const loadingList = ref(true)

async function loadBackups() {
  loadingList.value = true
  const res = await apiPgListBackups(props.instance.id)
  if (res && res.ok) backups.value = await res.json()
  loadingList.value = false
}

async function doBackup() {
  if (!database.value.trim()) return
  backing.value = true
  const res = await apiPgBackup(props.instance.id, database.value.trim())
  backing.value = false
  if (!res || !res.ok) {
    const d = await res?.json().catch(() => ({}))
    toastStore.showToast(d.detail || 'Erreur lors de la sauvegarde', true)
    return
  }
  const data = await res.json()
  toastStore.showToast(`Sauvegarde créée : ${data.filename} (${formatSize(data.size)})`)
  loadBackups()
}

async function deleteBackup(filename) {
  if (!confirm(`Supprimer la sauvegarde « ${filename} » ?`)) return
  const res = await apiPgDeleteBackup(props.instance.id, filename)
  if (res && res.ok) {
    toastStore.showToast('Sauvegarde supprimée')
    loadBackups()
  } else {
    toastStore.showToast('Erreur lors de la suppression', true)
  }
}

function downloadUrl(filename) {
  return `/api/postgres/${props.instance.id}/backups/${encodeURIComponent(filename)}`
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes > 1e9) return `${(bytes / 1e9).toFixed(1)} GB`
  if (bytes > 1e6) return `${(bytes / 1e6).toFixed(1)} MB`
  return `${(bytes / 1e3).toFixed(0)} KB`
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

onMounted(loadBackups)
</script>

<style scoped>
.backup-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.35);
  display: flex; align-items: center; justify-content: center;
}
.backup-panel {
  background: var(--white); border-radius: 12px;
  width: 560px; max-width: 95vw;
  max-height: 85vh; display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15); overflow: hidden;
}
.backup-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: 18px 20px; border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.backup-title { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.backup-sub { font-size: 11.5px; color: var(--text-muted); margin-top: 3px; }
.close-btn {
  background: none; border: none; cursor: pointer; color: var(--text-muted);
  padding: 4px; border-radius: 6px;
}
.close-btn:hover { background: var(--content-bg); }

.new-backup-row {
  display: flex; gap: 8px; padding: 16px 20px;
  border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.db-input {
  flex: 1; border: 1.5px solid var(--border); border-radius: 8px;
  padding: 7px 11px; font-size: 13px; font-family: inherit;
  background: var(--white); color: var(--text-primary); outline: none;
}
.db-input:focus { border-color: var(--accent); }

.backup-section-label {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.7px; color: var(--text-muted);
  padding: 14px 20px 8px; display: flex; align-items: center; gap: 6px; flex-shrink: 0;
}
.count {
  background: #F3F4F6; color: #6B7280;
  font-size: 10px; padding: 0 6px; border-radius: 10px;
}

.backup-loading, .backup-empty { color: #9CA3AF; font-size: 13px; padding: 8px 20px 16px; }

.backup-list { overflow-y: auto; flex: 1; padding: 0 20px 16px; }
.backup-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-radius: 8px; border: 1px solid var(--border);
  background: var(--content-bg); margin-bottom: 6px;
}
.backup-info { min-width: 0; }
.backup-file { font-size: 12.5px; font-weight: 600; color: var(--text-primary); font-family: monospace; display: block; }
.backup-meta { font-size: 11.5px; color: var(--text-muted); }
.backup-actions { display: flex; gap: 5px; flex-shrink: 0; }

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
