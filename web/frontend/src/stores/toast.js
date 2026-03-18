import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useToastStore = defineStore('toast', () => {
  const message = ref('')
  const isError = ref(false)
  const visible = ref(false)
  let timer = null

  function showToast(msg, error = false) {
    message.value = msg
    isError.value = error
    visible.value = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      visible.value = false
    }, 3200)
  }

  return { message, isError, visible, showToast }
})
