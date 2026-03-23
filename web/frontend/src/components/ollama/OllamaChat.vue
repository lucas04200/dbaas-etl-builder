<template>
  <div class="chat-overlay" @click.self="$emit('close')">
    <div class="chat-panel">
      <div class="chat-header">
        <div>
          <div class="chat-title">Chat — <span style="color:var(--accent)">{{ model }}</span></div>
          <div class="chat-subtitle">Test rapide via DataForge</div>
        </div>
        <button class="chat-close" @click="$emit('close')">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </button>
      </div>

      <div class="chat-messages" ref="messagesEl">
        <div v-if="!messages.length" class="chat-empty">
          Envoyez un message pour commencer…
        </div>
        <div
          v-for="(msg, i) in messages"
          :key="i"
          :class="['chat-msg', msg.role]"
        >
          <div class="chat-bubble">{{ msg.content }}</div>
        </div>
        <div v-if="thinking" class="chat-msg assistant">
          <div class="chat-bubble chat-thinking">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          </div>
        </div>
      </div>

      <div class="chat-input-row">
        <textarea
          v-model="input"
          class="chat-input"
          placeholder="Votre message…"
          rows="1"
          @keydown.enter.exact.prevent="send"
          @input="autoResize"
          ref="inputEl"
        ></textarea>
        <button class="btn btn-primary" :disabled="!input.trim() || thinking" @click="send">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M1 7h12M7 1l6 6-6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
      <div class="chat-hint">Entrée pour envoyer · Shift+Entrée pour nouvelle ligne</div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { useToastStore } from '../../stores/toast.js'
import { apiOllamaChat } from '../../lib/api.js'

const props = defineProps({
  instanceId: { type: Number, required: true },
  model: { type: String, required: true },
})
defineEmits(['close'])

const toastStore = useToastStore()
const messages = ref([])
const input = ref('')
const thinking = ref(false)
const messagesEl = ref(null)
const inputEl = ref(null)

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

async function send() {
  const text = input.value.trim()
  if (!text || thinking.value) return
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  if (inputEl.value) { inputEl.value.style.height = 'auto' }
  thinking.value = true
  await nextTick()
  scrollBottom()

  const history = messages.value.map(m => ({ role: m.role, content: m.content }))
  const res = await apiOllamaChat(props.instanceId, props.model, history)
  thinking.value = false

  if (!res || !res.ok) {
    toastStore.showToast('Erreur lors de la génération', true)
    return
  }
  const data = await res.json()
  const reply = data.message?.content || '(réponse vide)'
  messages.value.push({ role: 'assistant', content: reply })
  await nextTick()
  scrollBottom()
}

function scrollBottom() {
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}
</script>

<style scoped>
.chat-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.35);
  display: flex; align-items: center; justify-content: center;
}
.chat-panel {
  background: var(--white);
  border-radius: 14px;
  width: 600px; max-width: 95vw;
  height: 520px; max-height: 90vh;
  display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.18);
  overflow: hidden;
}
.chat-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.chat-title { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.chat-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.chat-close {
  background: none; border: none; cursor: pointer; color: var(--text-muted);
  padding: 4px; border-radius: 6px;
}
.chat-close:hover { background: var(--content-bg); color: var(--text-primary); }

.chat-messages {
  flex: 1; overflow-y: auto; padding: 16px 20px;
  display: flex; flex-direction: column; gap: 10px;
}
.chat-empty { color: #9CA3AF; font-size: 13px; text-align: center; margin-top: 40px; }

.chat-msg { display: flex; }
.chat-msg.user { justify-content: flex-end; }
.chat-msg.assistant { justify-content: flex-start; }

.chat-bubble {
  max-width: 78%; padding: 10px 14px; border-radius: 12px;
  font-size: 13.5px; line-height: 1.55; white-space: pre-wrap; word-break: break-word;
}
.chat-msg.user .chat-bubble {
  background: var(--accent); color: #fff; border-bottom-right-radius: 4px;
}
.chat-msg.assistant .chat-bubble {
  background: var(--content-bg); color: var(--text-primary);
  border: 1px solid var(--border); border-bottom-left-radius: 4px;
}

.chat-thinking {
  display: flex; align-items: center; gap: 5px; padding: 12px 16px;
}
.dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #9CA3AF; animation: bounce 1.2s infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }

.chat-input-row {
  display: flex; gap: 8px; padding: 12px 16px 8px;
  border-top: 1px solid var(--border); flex-shrink: 0;
}
.chat-input {
  flex: 1; border: 1.5px solid var(--border); border-radius: 8px;
  padding: 8px 12px; font-size: 13.5px; font-family: inherit;
  resize: none; outline: none; background: var(--white);
  color: var(--text-primary); line-height: 1.5; min-height: 38px;
}
.chat-input:focus { border-color: var(--accent); }
.chat-hint { font-size: 11px; color: var(--text-muted); text-align: right; padding: 0 16px 10px; flex-shrink: 0; }
</style>
