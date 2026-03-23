<template>
  <!-- database -->
  <svg v-if="category === 'database'" width="15" height="15" viewBox="0 0 15 15" fill="none">
    <ellipse cx="7.5" cy="3.5" rx="5" ry="1.8" stroke="currentColor" stroke-width="1.3"/>
    <path d="M2.5 3.5v4c0 1 2.24 1.8 5 1.8s5-.8 5-1.8v-4" stroke="currentColor" stroke-width="1.3"/>
    <path d="M2.5 7.5v4c0 1 2.24 1.8 5 1.8s5-.8 5-1.8v-4" stroke="currentColor" stroke-width="1.3"/>
  </svg>
  <!-- analytics / bi -->
  <svg v-else-if="category === 'analytics'" width="15" height="15" viewBox="0 0 15 15" fill="none">
    <rect x="1.5" y="8" width="3" height="5.5" rx="0.8" stroke="currentColor" stroke-width="1.3"/>
    <rect x="6" y="5" width="3" height="8.5" rx="0.8" stroke="currentColor" stroke-width="1.3"/>
    <rect x="10.5" y="2" width="3" height="11.5" rx="0.8" stroke="currentColor" stroke-width="1.3"/>
  </svg>
  <!-- etl / pipelines -->
  <svg v-else-if="category === 'etl'" width="15" height="15" viewBox="0 0 15 15" fill="none">
    <path d="M1.5 4.5h12M1.5 7.5h8M1.5 10.5h5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
    <path d="M11 6l2.5 1.5L11 9" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
  <!-- api / gateway -->
  <svg v-else-if="category === 'api'" width="15" height="15" viewBox="0 0 15 15" fill="none">
    <path d="M2 7.5h11M9.5 4l4 3.5-4 3.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="4" cy="7.5" r="1.5" stroke="currentColor" stroke-width="1.3"/>
  </svg>
  <!-- cache -->
  <svg v-else-if="category === 'cache'" width="15" height="15" viewBox="0 0 15 15" fill="none">
    <rect x="1.5" y="1.5" width="12" height="4" rx="1" stroke="currentColor" stroke-width="1.3"/>
    <rect x="1.5" y="9.5" width="12" height="4" rx="1" stroke="currentColor" stroke-width="1.3"/>
    <path d="M7.5 5.5v4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
  </svg>
  <!-- storage -->
  <svg v-else-if="category === 'storage'" width="15" height="15" viewBox="0 0 15 15" fill="none">
    <path d="M2 5l5.5-3 5.5 3v5l-5.5 3L2 10V5z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>
    <path d="M2 5l5.5 3 5.5-3M7.5 8v5" stroke="currentColor" stroke-width="1.3"/>
  </svg>
  <!-- ai -->
  <svg v-else-if="category === 'ai'" width="15" height="15" viewBox="0 0 15 15" fill="none">
    <circle cx="7.5" cy="7.5" r="5.5" stroke="currentColor" stroke-width="1.3"/>
    <path d="M5 7.5c0-1.38 1.12-2.5 2.5-2.5S10 6.12 10 7.5 8.88 10 7.5 10" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
    <circle cx="7.5" cy="7.5" r="1" fill="currentColor"/>
  </svg>
  <!-- fallback -->
  <svg v-else width="15" height="15" viewBox="0 0 15 15" fill="none">
    <rect x="1.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.3"/>
    <rect x="8.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.3"/>
    <rect x="1.5" y="8.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.3"/>
    <rect x="8.5" y="8.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.3"/>
  </svg>
</template>

<script setup>
defineProps({
  category: { type: String, required: true },
})
</script>
