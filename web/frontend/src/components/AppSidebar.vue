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
    </div>

    <div class="sidebar-section">
      <div class="sidebar-section-label">Services</div>
      <router-link to="/databases" class="nav-item" :class="{ active: route.path === '/databases' }">
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
          <ellipse cx="7.5" cy="3.5" rx="5" ry="1.8" stroke="currentColor" stroke-width="1.3"/>
          <path d="M2.5 3.5v4c0 1 2.24 1.8 5 1.8s5-.8 5-1.8v-4" stroke="currentColor" stroke-width="1.3"/>
          <path d="M2.5 7.5v4c0 1 2.24 1.8 5 1.8s5-.8 5-1.8v-4" stroke="currentColor" stroke-width="1.3"/>
        </svg>
        Bases de données
      </router-link>
      <router-link to="/n8n" class="nav-item" :class="{ active: route.path === '/n8n' }">
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
          <circle cx="2.5" cy="7.5" r="1.5" stroke="currentColor" stroke-width="1.3"/>
          <circle cx="7.5" cy="2.5" r="1.5" stroke="currentColor" stroke-width="1.3"/>
          <circle cx="12.5" cy="7.5" r="1.5" stroke="currentColor" stroke-width="1.3"/>
          <circle cx="7.5" cy="12.5" r="1.5" stroke="currentColor" stroke-width="1.3"/>
          <path d="M4 7.5h2M9 7.5h2M7.5 4v2M7.5 9v2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
        n8n
      </router-link>
    </div>

    <div class="sidebar-spacer"></div>

    <div class="sidebar-bottom">
      <router-link to="/security" class="nav-item" :class="{ active: route.path === '/security' }">
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
import { useRoute, useRouter } from 'vue-router'
import { apiLogout } from '../lib/api.js'
import { useAuthStore } from '../stores/auth.js'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

async function doLogout() {
  await apiLogout()
  authStore.clearUser()
  router.push('/login')
}
</script>
