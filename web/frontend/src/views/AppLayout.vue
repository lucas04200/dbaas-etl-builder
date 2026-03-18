<template>
  <div style="display:flex;min-height:100vh">
    <AppSidebar />
    <div class="main">
      <AppTopbar />
      <div class="content" :style="contentStyle">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '../components/AppSidebar.vue'
import AppTopbar from '../components/AppTopbar.vue'

const route = useRoute()

const contentStyle = computed(() => {
  if (route.path === '/catalog') {
    return { padding: '0', overflow: 'hidden' }
  }
  return {}
})
</script>
