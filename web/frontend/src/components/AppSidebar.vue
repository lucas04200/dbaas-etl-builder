<template>
  <nav class="sidebar">
    <div class="sidebar-logo">
      <div class="logo-icon">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <rect x="1" y="1" width="6" height="6" rx="1.5" fill="white"/>
          <rect x="9" y="1" width="6" height="6" rx="1.5" fill="white" opacity="0.55"/>
          <rect x="1" y="9" width="6" height="6" rx="1.5" fill="white" opacity="0.55"/>
          <rect x="9" y="9" width="6" height="6" rx="1.5" fill="white" opacity="0.25"/>
        </svg>
      </div>
      <span class="logo-name">DataForge</span>
    </div>

    <!-- Gestion -->
    <div class="sidebar-section">
      <div class="sidebar-section-label">Gestion</div>
      <router-link to="/catalog" class="nav-item" :class="{ active: route.path === '/catalog' }">
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
          <rect x="1.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.3"/>
          <rect x="8.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.3"/>
          <rect x="1.5" y="8.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.3"/>
          <rect x="8.5" y="8.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.3"/>
        </svg>
        Catalog
      </router-link>
      <router-link to="/library" class="nav-item" :class="{ active: route.path === '/library' }">
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
          <rect x="1.5" y="2" width="3" height="11" rx="0.5" stroke="currentColor" stroke-width="1.3"/>
          <rect x="6" y="2" width="3" height="11" rx="0.5" stroke="currentColor" stroke-width="1.3"/>
          <path d="M11 2l2.5 10.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
        Bibliothèque
      </router-link>
    </div>

    <!-- Services actifs (filtrés depuis la bibliothèque) -->
    <div class="sidebar-section" v-if="enabledServices.length">
      <div class="sidebar-section-label">Services</div>
      <router-link
        v-for="svc in enabledServices"
        :key="svc.id"
        :to="svc.route"
        class="nav-item"
        :class="{ active: route.path === svc.route }"
      >
        <SvcIcon :category="svc.category" />
        {{ svc.name }}
      </router-link>
    </div>
    <div class="sidebar-section" v-else-if="libraryStore.enabledServices !== null">
      <div class="sidebar-section-label">Services</div>
      <div class="nav-hint">
        <router-link to="/library" class="nav-hint-link">+ Ajouter depuis la bibliothèque</router-link>
      </div>
    </div>

    <div class="sidebar-spacer"></div>

    <div class="sidebar-bottom">
      <router-link v-if="isAdmin" to="/security" class="nav-item" :class="{ active: route.path === '/security' }">
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
          <path d="M7.5 1.5 2.5 3.75V7c0 3 2.2 5.8 5 6.5 2.8-.7 5-3.5 5-6.5V3.75L7.5 1.5z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>
          <path d="M5.25 7.5 6.75 9 10 5.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Sécurité
      </router-link>
      <a class="nav-item logout" @click.prevent="doLogout">
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
          <path d="M5.5 2.5H3a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h2.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
          <path d="M10 5 13 7.5 10 10" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
          <line x1="13" y1="7.5" x2="6" y2="7.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
        Se déconnecter
      </a>
    </div>
  </nav>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useLibraryStore } from '../stores/library.js'
import { apiLogout } from '../lib/api.js'
import { SERVICES } from '../data/services.js'
import SvcIcon from './SvcIcon.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const libraryStore = useLibraryStore()

const isAdmin = computed(() => authStore.currentUser?.role === 'admin')

// Only services with a management page appear in the sidebar
const enabledServices = computed(() =>
  SERVICES.filter(s => s.route && libraryStore.isEnabled(s.id))
)

onMounted(() => libraryStore.loadEnabled())

async function doLogout() {
  await apiLogout()
  authStore.clearUser()
  router.push('/login')
}
</script>

<style scoped>
.nav-hint { padding: 6px 18px; }
.nav-hint-link { font-size: 12px; color: #3D4A60; text-decoration: none; transition: color 0.12s; }
.nav-hint-link:hover { color: var(--accent); }
</style>
