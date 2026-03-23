import { defineStore } from 'pinia'
import { ref } from 'vue'
import { DEFAULT_ENABLED } from '../data/services.js'

export const useLibraryStore = defineStore('library', () => {
  // null = not yet loaded (avoids flash with wrong defaults)
  const enabledServices = ref(null)
  const pullStatus = ref({})
  let _pollInterval = null

  function isEnabled(serviceId) {
    if (!enabledServices.value) return false
    return enabledServices.value.has(serviceId)
  }

  async function loadEnabled() {
    try {
      const res = await fetch('/api/library/enabled')
      if (res.ok) {
        const data = await res.json()
        enabledServices.value = new Set(data.enabled)
        return
      }
    } catch { /* fall through to defaults */ }
    // Backend not reachable → use defaults
    enabledServices.value = new Set(DEFAULT_ENABLED)
  }

  async function setEnabled(serviceId, enabled) {
    const method = enabled ? 'POST' : 'DELETE'
    const res = await fetch(`/api/library/${serviceId}/enable`, { method })
    if (res.ok) {
      if (!enabledServices.value) enabledServices.value = new Set()
      if (enabled) {
        enabledServices.value.add(serviceId)
      } else {
        enabledServices.value.delete(serviceId)
      }
    }
  }

  async function pullImage(serviceId) {
    const res = await fetch(`/api/library/${serviceId}/pull`, { method: 'POST' })
    if (!res.ok) throw new Error('Pull failed')
    const data = await res.json()
    pullStatus.value[data.image] = 'pulling'
    startPolling()
  }

  async function loadPullStatus() {
    try {
      const res = await fetch('/api/library/pull-status')
      if (res.ok) pullStatus.value = await res.json()
    } catch { /* ignore */ }
  }

  function startPolling() {
    if (_pollInterval) return
    _pollInterval = setInterval(async () => {
      await loadPullStatus()
      const stillPulling = Object.values(pullStatus.value).some(s => s === 'pulling')
      if (!stillPulling) {
        clearInterval(_pollInterval)
        _pollInterval = null
      }
    }, 2000)
  }

  return { enabledServices, pullStatus, isEnabled, loadEnabled, setEnabled, pullImage, loadPullStatus, startPolling }
})
