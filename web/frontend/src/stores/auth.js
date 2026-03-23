import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref(null)

  function setUser(user) {
    currentUser.value = user
  }

  function clearUser() {
    currentUser.value = null
  }

  return { currentUser, setUser, clearUser }
})
