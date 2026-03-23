<template>
  <div :class="['toast', { show: toastStore.visible, error: toastStore.isError }]">
    {{ toastStore.message }}
  </div>
</template>

<script setup>
import { useToastStore } from '../stores/toast.js'

const toastStore = useToastStore()
</script>
