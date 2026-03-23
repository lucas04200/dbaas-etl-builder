<template>
  <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--content-bg)">
    <div style="background:var(--white);border:1px solid var(--border);border-radius:14px;padding:40px;width:380px;max-width:92vw;box-shadow:0 8px 40px rgba(0,0,0,0.08)">
      <div style="display:flex;flex-direction:column;align-items:center;gap:10px;margin-bottom:20px">
        <div style="display:flex;align-items:center;gap:10px">
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
        <h2 style="font-size:20px;font-weight:700;margin-bottom:2px;letter-spacing:-0.3px;text-align:center">Bienvenue sur DataForge</h2>
        <p style="font-size:13.5px;color:var(--text-secondary);text-align:center">Créez votre compte administrateur pour commencer.</p>
      </div>
      <div class="form-group" style="margin-bottom:14px">
        <label>Nom d'utilisateur</label>
        <input
          type="text"
          v-model="username"
          placeholder="admin"
          @keyup.enter="doSetup"
          style="width:100%"
        >
      </div>
      <div class="form-group" style="margin-bottom:14px">
        <label>Adresse e-mail <span style="color:#EF4444;font-weight:400">*</span></label>
        <input
          type="email"
          v-model="email"
          placeholder="admin@example.com"
          @keyup.enter="doSetup"
          style="width:100%"
        >
      </div>
      <div class="form-group" style="margin-bottom:14px">
        <label>Mot de passe</label>
        <input
          type="password"
          v-model="password"
          placeholder="••••••••"
          @keyup.enter="doSetup"
          style="width:100%"
        >
      </div>
      <div class="form-group" style="margin-bottom:22px">
        <label>Confirmer le mot de passe</label>
        <input
          type="password"
          v-model="confirmPassword"
          placeholder="••••••••"
          @keyup.enter="doSetup"
          style="width:100%"
        >
      </div>
      <div v-if="error" style="color:var(--error);font-size:13px;margin-bottom:14px">{{ error }}</div>
      <button class="btn btn-primary" style="width:100%;justify-content:center" :disabled="loading" @click="doSetup">
        {{ loading ? 'Création…' : 'Créer le compte' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiSetup } from '../lib/api.js'

const router = useRouter()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

async function doSetup() {
  if (!username.value || !email.value || !password.value || !confirmPassword.value) {
    error.value = 'Tous les champs sont obligatoires'
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = 'Les mots de passe ne correspondent pas'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await apiSetup({ username: username.value, email: email.value, password: password.value })
    if (!res || !res.ok) {
      const d = await res.json().catch(() => ({}))
      error.value = d.detail || 'Erreur lors de la création du compte'
      loading.value = false
      return
    }
    router.push('/login')
  } catch {
    error.value = 'Erreur de connexion'
  } finally {
    loading.value = false
  }
}
</script>
