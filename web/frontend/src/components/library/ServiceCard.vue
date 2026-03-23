<template>
  <div class="svc-card" :class="{ 'is-enabled': enabled }">
    <div class="svc-card-header">
      <div class="svc-icon" :style="{ background: service.color + '18', color: service.color }">
        <svg v-if="service.category === 'database'" width="18" height="18" viewBox="0 0 15 15" fill="none">
          <ellipse cx="7.5" cy="3.5" rx="5" ry="1.8" stroke="currentColor" stroke-width="1.3"/>
          <path d="M2.5 3.5v4c0 1 2.24 1.8 5 1.8s5-.8 5-1.8v-4" stroke="currentColor" stroke-width="1.3"/>
          <path d="M2.5 7.5v4c0 1 2.24 1.8 5 1.8s5-.8 5-1.8v-4" stroke="currentColor" stroke-width="1.3"/>
        </svg>
        <svg v-else-if="service.category === 'analytics'" width="18" height="18" viewBox="0 0 15 15" fill="none">
          <rect x="1.5" y="9" width="3" height="5" rx="0.5" stroke="currentColor" stroke-width="1.3"/>
          <rect x="6" y="5.5" width="3" height="8.5" rx="0.5" stroke="currentColor" stroke-width="1.3"/>
          <rect x="10.5" y="2" width="3" height="12" rx="0.5" stroke="currentColor" stroke-width="1.3"/>
        </svg>
        <svg v-else-if="service.category === 'etl'" width="18" height="18" viewBox="0 0 15 15" fill="none">
          <path d="M7.5 1.5L9.5 6H13L9.8 8.8 11 13 7.5 10.5 4 13l1.2-4.2L2 6h3.5z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>
        </svg>
        <svg v-else-if="service.category === 'api'" width="18" height="18" viewBox="0 0 15 15" fill="none">
          <path d="M2 5h11M2 10h11" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
          <path d="M5 2l-3 5.5 3 5.5M10 2l3 5.5-3 5.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <svg v-else-if="service.category === 'cache'" width="18" height="18" viewBox="0 0 15 15" fill="none">
          <ellipse cx="7.5" cy="4" rx="5" ry="2" stroke="currentColor" stroke-width="1.3"/>
          <ellipse cx="7.5" cy="7.5" rx="5" ry="2" stroke="currentColor" stroke-width="1.3"/>
          <ellipse cx="7.5" cy="11" rx="5" ry="2" stroke="currentColor" stroke-width="1.3"/>
          <path d="M2.5 4v7M12.5 4v7" stroke="currentColor" stroke-width="1.3"/>
        </svg>
        <svg v-else width="18" height="18" viewBox="0 0 15 15" fill="none">
          <path d="M2 11V6l5.5-4L13 6v5a1 1 0 01-1 1H3a1 1 0 01-1-1z" stroke="currentColor" stroke-width="1.3"/>
          <path d="M5.5 12V8.5h4V12" stroke="currentColor" stroke-width="1.3"/>
        </svg>
      </div>
      <div class="svc-info">
        <div class="svc-name">{{ service.name }} <span class="svc-version">v{{ service.version }}</span></div>
        <span class="svc-license" :class="service.licenseType">{{ service.license }}</span>
      </div>
      <div class="svc-enabled-badge" v-if="enabled">Actif</div>
    </div>

    <p class="svc-desc">{{ service.description }}</p>

    <div class="svc-tags">
      <span class="svc-tag" v-for="tag in service.tags.slice(0, 4)" :key="tag">{{ tag }}</span>
    </div>

    <div class="svc-image">
      <code>{{ service.dockerImage }}</code>
    </div>

    <div class="svc-actions">
      <button
        class="btn btn-sm"
        :class="actionBtnClass"
        :disabled="pullState === 'pulling'"
        @click.stop="$emit('action', service)"
      >
        <svg v-if="pullState === 'pulling'" width="12" height="12" viewBox="0 0 12 12" fill="none" class="spin">
          <circle cx="6" cy="6" r="4.5" stroke="currentColor" stroke-width="1.5" stroke-dasharray="14" stroke-dashoffset="5"/>
        </svg>
        <svg v-else-if="enabled" width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M2 6h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <svg v-else-if="pullState === 'pulled'" width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M6 2v8M2 6h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <svg v-else width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M6 2v6M3 6l3 3 3-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ actionLabel }}
      </button>

      <!-- Deploy button (only if route exists and enabled) -->
      <router-link
        v-if="service.route && enabled"
        :to="service.route"
        class="btn btn-sm btn-secondary"
      >
        Gérer →
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  service: { type: Object, required: true },
  enabled: { type: Boolean, default: false },
  pullStatus: { type: String, default: 'unknown' }, // 'not_pulled' | 'pulling' | 'pulled' | 'error' | 'unknown'
})

defineEmits(['action'])

const pullState = computed(() => {
  const s = props.pullStatus
  if (s === 'pulling') return 'pulling'
  if (s === 'pulled') return 'pulled'
  if (s === 'error') return 'error'
  return 'idle'
})

const actionLabel = computed(() => {
  if (pullState.value === 'pulling') return 'Téléchargement…'
  if (pullState.value === 'error') return 'Erreur — Réessayer'
  if (props.enabled) return 'Retirer'
  if (pullState.value === 'pulled') return 'Ajouter'
  return 'Télécharger'
})

const actionBtnClass = computed(() => {
  if (pullState.value === 'error') return 'btn-danger'
  if (props.enabled) return 'btn-ghost-blue'
  return 'btn-primary'
})
</script>

<style scoped>
.svc-card {
  background: var(--white);
  border: 1.5px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.svc-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.07); }
.svc-card.is-enabled { border-color: var(--accent); }

.svc-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.svc-icon {
  width: 38px; height: 38px;
  border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.svc-info { flex: 1; min-width: 0; }
.svc-name { font-size: 14px; font-weight: 700; color: var(--text-primary); }
.svc-version { font-size: 11px; font-weight: 500; color: var(--text-muted); margin-left: 4px; }
.svc-license {
  display: inline-block;
  font-size: 10.5px; font-weight: 600;
  padding: 1px 7px; border-radius: 20px; margin-top: 3px;
}
.svc-license.permissive { background: #D1FAE5; color: #065F46; }
.svc-license.copyleft { background: #FEF3C7; color: #92400E; }
.svc-license.source-available { background: #FEE2E2; color: #991B1B; }

.svc-enabled-badge {
  font-size: 10px; font-weight: 700;
  background: var(--accent-dim); color: var(--accent);
  padding: 2px 8px; border-radius: 20px;
}

.svc-desc { font-size: 13px; color: var(--text-secondary); line-height: 1.5; flex: 1; }

.svc-tags { display: flex; flex-wrap: wrap; gap: 5px; }
.svc-tag {
  font-size: 11px; color: var(--text-muted);
  background: var(--content-bg);
  border: 1px solid var(--border);
  padding: 1px 7px; border-radius: 20px;
}

.svc-image {
  background: #F3F4F6; border-radius: 6px;
  padding: 6px 10px;
}
.svc-image code { font-size: 11.5px; color: #374151; font-family: 'SF Mono', 'Fira Mono', monospace; }

.svc-actions { display: flex; gap: 7px; flex-wrap: wrap; align-items: center; }

.btn-success { background: #D1FAE5; color: #065F46; border: 1.5px solid #6EE7B7; }
.btn-danger { background: #FEE2E2; color: #991B1B; border: 1.5px solid #FECACA; }
.btn-ghost-blue { background: transparent; color: var(--accent); border: 1.5px solid #C7D2FE; }
.btn-ghost-blue:hover { background: var(--accent-dim); }

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
