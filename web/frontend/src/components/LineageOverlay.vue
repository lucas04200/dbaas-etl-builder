<template>
  <!-- Full‑size SVG placed over the sidebar -->
  <svg class="lineage-overlay" :width="width" :height="height">
    <line
      v-for="(c, i) in connections"
      :key="i"
      :x1="c.from.x"
      :y1="c.from.y"
      :x2="c.to.x"
      :y2="c.to.y"
      stroke="var(--accent)"
      stroke-width="2"
      stroke-dasharray="4 2"
      marker-end="url(#arrow)"
    />
    <!-- Arrow head definition -->
    <defs>
      <marker id="arrow" markerWidth="8" markerHeight="8" refX="5" refY="3" orient="auto">
        <path d="M0,0 L0,6 L9,3 z" fill="var(--accent)" />
      </marker>
    </defs>
  </svg>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

/** Props
 *  `serviceRefs` – map of service‑id → DOM element (the <router‑link> for that service)
 *  `rawConnections` – array of `{ fromId: string, toId: string }` coming from the store
 */
interface Props {
  serviceRefs: Record<string, HTMLElement | null>
  rawConnections: { fromId: string; toId: string }[]
}
const props = defineProps<Props>()

// Reactive list of line coordinates used by the template
const connections = ref<
  { from: { x: number; y: number }; to: { x: number; y: number } }[]
>([])

// Size of the overlay (updated on mount / resize)
const width = ref(0)
const height = ref(0)

function updateSize() {
  const sidebar = document.querySelector('.sidebar')
  if (sidebar) {
    width.value = sidebar.clientWidth
    height.value = sidebar.scrollHeight
  }
}

function computeLines() {
  const lines: typeof connections.value = []
  for (const conn of props.rawConnections) {
    const fromEl = props.serviceRefs[conn.fromId]
    const toEl = props.serviceRefs[conn.toId]
    if (fromEl && toEl) {
      const fromRect = fromEl.getBoundingClientRect()
      const toRect = toEl.getBoundingClientRect()
      const sidebarRect = document.querySelector('.sidebar')!.getBoundingClientRect()

      // Coordinates relative to the sidebar container
      const from = {
        x: fromRect.right - sidebarRect.left,
        y: fromRect.top + fromRect.height / 2 - sidebarRect.top,
      }
      const to = {
        x: toRect.left - sidebarRect.left,
        y: toRect.top + toRect.height / 2 - sidebarRect.top,
      }
      lines.push({ from, to })
    }
  }
  connections.value = lines
}

onMounted(() => {
  updateSize()
  computeLines()
  window.addEventListener('resize', () => {
    updateSize()
    computeLines()
  })
})

// Re‑compute when the underlying connections change
watch(() => props.rawConnections, computeLines, { deep: true })
watch(() => props.serviceRefs, computeLines, { deep: true })
</script>

<style scoped>
.lineage-overlay {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none; /* allow clicks to pass through */
  overflow: visible;
}
</style>
