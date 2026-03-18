<template>
  <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--content-bg)">
    <div style="background:var(--white);border:1px solid var(--border);border-radius:14px;padding:40px;width:380px;max-width:92vw;box-shadow:0 8px 40px rgba(0,0,0,0.08)">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:28px">
        <div class="logo-icon">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="1" y="1" width="6" height="6" rx="1.5" fill="white"/>
            <rect x="9" y="1" width="6" height="6" rx="1.5" fill="white" opacity="0.55"/>
            <rect x="1" y="9" width="6" height="6" rx="1.5" fill="white" opacity="0.55"/>
            <rect x="9" y="9" width="6" height="6" rx="1.5" fill="white" opacity="0.25"/>
          </svg>
        </div>
        <span class="logo-name" style="color:var(--text-primary)">DataForge</span>
      </div>
      <h2 style="font-size:20px;font-weight:700;margin-bottom:6px;letter-spacing:-0.3px">Connexion</h2>
      <p style="font-size:13.5px;color:var(--text-secondary);margin-bottom:24px">Connectez-vous à votre espace DataForge</p>
      <div class="form-group" style="margin-bottom:14px">
        <label>Nom d'utilisateur</label>
        <input
          type="text"
          v-model="username"
          placeholder="admin"
          @keyup.enter="doLogin"
          style="width:100%"
        >
      </div>
      <div class="form-group" style="margin-bottom:22px">
        <label>Mot de passe</label>
        <input
          type="password"
          v-model="password"
          placeholder="••••••••"
          @keyup.enter="doLogin"
          style="width:100%"
        >
      </div>
      <div v-if="error" style="color:var(--error);font-size:13px;margin-bottom:14px">{{ error }}</div>
      <button class="btn btn-primary" style="width:100%;justify-content:center" :disabled="loading" @click="doLogin">
        {{ loading ? 'Connexion…' : 'Se connecter' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiLogin, apiMe } from '../lib/api.js'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function doLogin() {
  if (!username.value || !password.value) {
    error.value = 'Remplissez tous les champs'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await apiLogin(username.value, password.value)
    if (!res.ok) {
      const d = await res.json().catch(() => ({}))
      error.value = d.detail || 'Identifiants incorrects'
      loading.value = false
      return
    }
    const meRes = await apiMe()
    if (meRes && meRes.ok) {
      authStore.setUser(await meRes.json())
    }
    router.push('/databases')
  } catch {
    error.value = 'Erreur de connexion'
  } finally {
    loading.value = false
  }
}
</script>
