<template>
  <div v-if="modelValue" class="modal-overlay open" @click.self="$emit('update:modelValue', false)">
    <div class="modal">
      <div class="modal-head">
        <h3>{{ title }}</h3>
        <button class="modal-close" @click="$emit('update:modelValue', false)">×</button>
      </div>
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: Boolean,
  title: String,
})
defineEmits(['update:modelValue'])
</script>
