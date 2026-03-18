<template>
  <div class="topbar">
    <span class="topbar-title">{{ title }}</span>
    <div class="topbar-user">
      <div class="avatar">{{ avatarLetter }}</div>
      <span>{{ authStore.currentUser?.username }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const authStore = useAuthStore()
const route = useRoute()

const title = computed(() => {
  const map = {
    '/databases': 'Bases de données',
    '/catalog': 'Catalog',
    '/n8n': 'n8n',
    '/security': 'Sécurité',
  }
  return map[route.path] || 'DataForge'
})

const avatarLetter = computed(() => {
  const u = authStore.currentUser?.username
  return u ? u[0].toUpperCase() : '?'
})
</script>
