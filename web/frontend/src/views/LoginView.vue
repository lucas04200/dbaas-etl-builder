<template>
  <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--content-bg)">
    <div style="background:var(--white);border:1px solid var(--border);border-radius:14px;padding:40px;width:380px;max-width:92vw;box-shadow:0 8px 40px rgba(0,0,0,0.08)">

      <div style="display:flex;flex-direction:column;align-items:center;gap:10px;margin-bottom:28px">
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
      </div>

      <!-- Toggle -->
      <div class="auth-tabs">
        <button :class="['auth-tab', { active: mode === 'login' }]" @click="switchMode('login')">Connexion</button>
        <button :class="['auth-tab', { active: mode === 'register' }]" @click="switchMode('register')">Créer un compte</button>
      </div>

      <!-- LOGIN -->
      <template v-if="mode === 'login'">
        <div class="form-group" style="margin-bottom:14px">
          <label>Adresse e-mail</label>
          <input type="email" v-model="email" placeholder="alice@exemple.com" @keyup.enter="doLogin" style="width:100%">
        </div>
        <div class="form-group" style="margin-bottom:22px">
          <label>Mot de passe</label>
          <input type="password" v-model="password" placeholder="••••••••" @keyup.enter="doLogin" style="width:100%">
        </div>
        <div v-if="error" class="auth-error">{{ error }}</div>
        <button class="btn btn-primary" style="width:100%;justify-content:center" :disabled="loading" @click="doLogin">
          {{ loading ? 'Connexion…' : 'Se connecter' }}
        </button>
      </template>

      <!-- REGISTER -->
      <template v-else>
        <div class="form-group" style="margin-bottom:14px">
          <label>Nom d'utilisateur</label>
          <input type="text" v-model="username" placeholder="alice" @keyup.enter="doRegister" style="width:100%">
        </div>
        <div class="form-group" style="margin-bottom:14px">
          <label>Adresse e-mail <span class="required">*</span></label>
          <input type="email" v-model="email" placeholder="alice@exemple.com" @keyup.enter="doRegister" style="width:100%">
        </div>
        <div class="form-group" style="margin-bottom:14px">
          <label>Mot de passe <span class="required">*</span></label>
          <input type="password" v-model="password" placeholder="••••••••" @keyup.enter="doRegister" style="width:100%">
        </div>
        <div class="form-group" style="margin-bottom:22px">
          <label>Confirmer le mot de passe <span class="required">*</span></label>
          <input type="password" v-model="confirmPassword" placeholder="••••••••" @keyup.enter="doRegister" style="width:100%">
        </div>
        <div v-if="error" class="auth-error">{{ error }}</div>
        <button class="btn btn-primary" style="width:100%;justify-content:center" :disabled="loading" @click="doRegister">
          {{ loading ? 'Création…' : 'Créer le compte' }}
        </button>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiLogin, apiMe } from '../lib/api.js'
import { apiRegister } from '../lib/api.js'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const authStore = useAuthStore()

const mode = ref('login')
const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

function switchMode(m) {
  mode.value = m
  error.value = ''
  username.value = ''
  email.value = ''
  password.value = ''
  confirmPassword.value = ''
}

async function doLogin() {
  if (!email.value || !password.value) { error.value = 'Remplissez tous les champs'; return }
  loading.value = true
  error.value = ''
  try {
    const res = await apiLogin(email.value, password.value)
    if (!res.ok) {
      const d = await res.json().catch(() => ({}))
      error.value = d.detail || 'Identifiants incorrects'
      return
    }
    const meRes = await apiMe()
    if (meRes && meRes.ok) authStore.setUser(await meRes.json())
    router.push('/databases')
  } catch {
    error.value = 'Erreur de connexion'
  } finally {
    loading.value = false
  }
}

async function doRegister() {
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
    const res = await apiRegister({ username: username.value, email: email.value, password: password.value })
    if (!res || !res.ok) {
      const d = await res?.json().catch(() => ({}))
      error.value = d.detail || 'Erreur lors de la création du compte'
      return
    }
    switchMode('login')
    error.value = ''
  } catch {
    error.value = 'Erreur de connexion'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-tabs {
  display: flex;
  gap: 4px;
  background: var(--content-bg, #F9FAFB);
  border-radius: 8px;
  padding: 4px;
  margin-bottom: 24px;
}
.auth-tab {
  flex: 1;
  padding: 7px 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}
.auth-tab.active {
  background: var(--white, #fff);
  color: var(--text-primary);
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.auth-error {
  color: var(--error, #EF4444);
  font-size: 13px;
  margin-bottom: 14px;
}
.required {
  color: #EF4444;
  font-weight: 400;
}
</style>
