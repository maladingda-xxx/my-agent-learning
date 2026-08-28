<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { marked } from 'marked'
import { useProviders } from './stores/providers.js'
import SettingsModal from './components/SettingsModal.vue'

const { models, selectedModel, selectModel, init: initProviders } = useProviders()

const messages = ref([])
const inputText = ref('')
const isLoading = ref(false)
const sessionId = ref(`session_${Date.now()}`)
const uploadStatus = ref('')
const sidebarOpen = ref(true)
const chatContainer = ref(null)
const inputRef = ref(null)
const showSettings = ref(false)
const showModelDropdown = ref(false)

// 对话历史列表（侧边栏）
const conversations = ref([
  { id: 'current', title: '新对话', active: true }
])

function renderMarkdown(text) {
  if (!text) return ''
  return marked.parse(text, { breaks: true })
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isLoading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  isLoading.value = true
  scrollToBottom()

  // 更新侧边栏标题
  if (messages.value.length === 1) {
    conversations.value[0].title = text.slice(0, 20) + (text.length > 20 ? '...' : '')
  }

  const assistantMsg = { role: 'assistant', content: '', sources: [] }
  messages.value.push(assistantMsg)

  try {
    const response = await fetch('/api/chat/rag/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: sessionId.value, model: selectedModel.value || undefined }),
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith('event: meta') || line.startsWith('event: done')) continue
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') break
          try {
            const parsed = JSON.parse(data)
            if (parsed.type === 'meta') {
              assistantMsg.sources = parsed.sources || []
              continue
            }
          } catch {}
          assistantMsg.content += data
          scrollToBottom()
        }
      }
    }
  } catch (err) {
    assistantMsg.content += `\n\n[请求失败: ${err.message}]`
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

async function handleFileSelect(event) {
  const file = event.target.files[0]
  if (!file) return

  uploadStatus.value = `正在上传: ${file.name}...`
  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await fetch('/api/upload/', { method: 'POST', body: formData })
    const result = await res.json()
    if (res.ok) {
      uploadStatus.value = `上传成功: ${file.name} (${result.chunks_stored || '?'} 个片段)`
    } else {
      uploadStatus.value = `上传失败: ${result.detail || '未知错误'}`
    }
  } catch (err) {
    uploadStatus.value = `上传失败: ${err.message}`
  }
  setTimeout(() => { uploadStatus.value = '' }, 4000)
  event.target.value = ''
}

async function clearSession() {
  try {
    await fetch(`/api/session/${sessionId.value}`, { method: 'DELETE' })
  } catch {}
  messages.value = []
  sessionId.value = `session_${Date.now()}`
  conversations.value[0].title = '新对话'
}

function newChat() {
  clearSession()
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function autoResize(event) {
  const el = event.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 150) + 'px'
}

function handleModelSelect(model) {
  selectModel(model)
  showModelDropdown.value = false
}

// 点击外部关闭下拉
function handleClickOutside(e) {
  if (showModelDropdown.value && !e.target.closest('.model-selector')) {
    showModelDropdown.value = false
  }
}

onMounted(() => {
  inputRef.value?.focus()
  initProviders()
  document.addEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: !sidebarOpen }">
      <div class="sidebar-header">
        <button class="icon-btn new-chat-btn" @click="newChat" title="新对话">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12h14"/>
          </svg>
        </button>
        <button class="icon-btn" @click="toggleSidebar" title="收起侧边栏">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 3H3M21 12H9M21 21H3"/>
          </svg>
        </button>
      </div>
      <nav class="sidebar-nav">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="nav-item"
          :class="{ active: conv.active }"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
          <span class="nav-item-title">{{ conv.title }}</span>
        </div>
      </nav>
      <div class="sidebar-footer">
        <label class="sidebar-action">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
          </svg>
          <span>上传文档</span>
          <input type="file" accept=".pdf,.txt,.md" @change="handleFileSelect" hidden />
        </label>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main">
      <!-- 顶栏 -->
      <header class="topbar">
        <button v-if="!sidebarOpen" class="icon-btn" @click="toggleSidebar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 3H3M21 12H9M21 21H3"/>
          </svg>
        </button>

        <!-- 模型选择下拉 -->
        <div class="model-selector" @click="showModelDropdown = !showModelDropdown">
          <span class="model-selector-text">{{ selectedModel || '选择模型' }}</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 9l6 6 6-6"/>
          </svg>
          <div v-if="showModelDropdown" class="model-dropdown" @click.stop>
            <div
              v-for="m in models"
              :key="m.model"
              class="model-option"
              :class="{ active: m.model === selectedModel }"
              @click="handleModelSelect(m.model)"
            >
              <span class="model-option-name">{{ m.model }}</span>
              <span class="model-option-provider">{{ m.provider }}</span>
            </div>
            <div v-if="models.length === 0" class="model-option empty">暂无模型，请先配置供应商</div>
            <div class="model-dropdown-footer" @click="showSettings = true; showModelDropdown = false">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 5v14M5 12h14"/>
              </svg>
              管理供应商
            </div>
          </div>
        </div>

        <button class="icon-btn" @click="showSettings = true" title="设置">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
          </svg>
        </button>
      </header>

      <!-- 上传状态提示 -->
      <Transition name="fade">
        <div v-if="uploadStatus" class="upload-toast">{{ uploadStatus }}</div>
      </Transition>

      <!-- 消息区 -->
      <div class="messages" ref="chatContainer">
        <!-- 空状态 -->
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
              <path d="M12 2a10 10 0 110 20 10 10 0 010-20z"/>
              <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
              <line x1="9" y1="9" x2="9.01" y2="9"/>
              <line x1="15" y1="9" x2="15.01" y2="9"/>
            </svg>
          </div>
          <h2>有什么可以帮你的？</h2>
          <p class="welcome-hint">支持基于文档的 RAG 问答，上传 PDF / TXT / Markdown 即可开始</p>
          <div class="suggestions">
            <button @click="inputText = '帮我总结一下上传的文档内容'">总结文档内容</button>
            <button @click="inputText = '这个项目使用了哪些技术栈？'">问技术栈</button>
            <button @click="inputText = '用简单的语言解释 RAG 是什么'">解释 RAG</button>
          </div>
        </div>

        <!-- 消息列表 -->
        <div v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="msg.role">
          <div class="avatar">
            <span v-if="msg.role === 'user'">你</span>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 2a10 10 0 110 20 10 10 0 010-20z"/>
              <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
            </svg>
          </div>
          <div class="msg-body">
            <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
            <div v-if="msg.sources && msg.sources.length" class="msg-sources">
              <details>
                <summary>引用来源 ({{ msg.sources.length }})</summary>
                <ul>
                  <li v-for="(s, i) in msg.sources" :key="i">
                    {{ s.source || '未知来源' }}
                    <span v-if="s.page"> · 第{{ s.page }}页</span>
                  </li>
                </ul>
              </details>
            </div>
          </div>
        </div>

        <!-- 加载指示器 -->
        <div v-if="isLoading && messages[messages.length-1]?.content === ''" class="msg-row assistant">
          <div class="avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 2a10 10 0 110 20 10 10 0 010-20z"/>
            </svg>
          </div>
          <div class="msg-body">
            <div class="thinking-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="input-wrapper">
        <form class="input-box" @submit.prevent="sendMessage">
          <textarea
            ref="inputRef"
            v-model="inputText"
            placeholder="发送消息..."
            :disabled="isLoading"
            rows="1"
            @keydown.enter.exact.prevent="sendMessage"
            @input="autoResize"
          ></textarea>
          <button type="submit" class="send-btn" :disabled="isLoading || !inputText.trim()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </form>
        <p class="input-hint">AI 可能会犯错，请注意甄别回答内容</p>
      </div>
    </main>

    <!-- 设置弹窗 -->
    <SettingsModal v-if="showSettings" @close="showSettings = false" />
  </div>
</template>

<style>
:root {
  --sidebar-width: 260px;
  --sidebar-bg: #171717;
  --main-bg: #212121;
  --msg-hover: #2a2a2a;
  --text-primary: #ececec;
  --text-secondary: #9a9a9a;
  --text-tertiary: #6b6b6b;
  --border-color: #2e2e2e;
  --accent: #10a37f;
  --accent-hover: #0d8c6d;
  --input-bg: #2f2f2f;
  --user-avatar-bg: #5a4fcf;
  --ai-avatar-bg: #10a37f;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Söhne', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--main-bg);
  color: var(--text-primary);
  height: 100vh;
  overflow: hidden;
}

.layout {
  display: flex;
  height: 100vh;
}

/* ===== 侧边栏 ===== */
.sidebar {
  width: var(--sidebar-width);
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease, opacity 0.2s ease;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: background 0.15s;
  font-size: 14px;
}

.nav-item:hover {
  background: var(--msg-hover);
}

.nav-item.active {
  background: var(--msg-hover);
  color: var(--text-primary);
}

.nav-item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--border-color);
}

.sidebar-action {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 14px;
  transition: background 0.15s;
}

.sidebar-action:hover {
  background: var(--msg-hover);
  color: var(--text-primary);
}

/* ===== 通用按钮 ===== */
.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.icon-btn:hover {
  background: var(--msg-hover);
  color: var(--text-primary);
}

/* ===== 主内容区 ===== */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  position: relative;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-color);
  min-height: 52px;
}

.model-badge {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
  text-align: center;
}

/* ===== 模型选择器 ===== */
.model-selector {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  flex: 1;
  justify-content: center;
}

.model-selector:hover {
  background: var(--msg-hover);
}

.model-selector-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  min-width: 260px;
  background: #1e1e1e;
  border: 1px solid #333;
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.5);
  z-index: 200;
  padding: 6px;
  max-height: 320px;
  overflow-y: auto;
  animation: dropIn 0.15s ease;
}

@keyframes dropIn {
  from { opacity: 0; transform: translateX(-50%) translateY(-4px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

.model-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.12s;
}

.model-option:hover {
  background: var(--msg-hover);
}

.model-option.active {
  background: rgba(16, 163, 127, 0.1);
}

.model-option.empty {
  color: var(--text-tertiary);
  font-size: 13px;
  cursor: default;
}

.model-option-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.model-option-provider {
  font-size: 11px;
  color: var(--text-tertiary);
  background: rgba(255,255,255,0.05);
  padding: 2px 8px;
  border-radius: 4px;
}

.model-dropdown-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  margin-top: 4px;
  border-top: 1px solid var(--border-color);
  font-size: 13px;
  color: var(--accent);
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.12s;
}

.model-dropdown-footer:hover {
  background: var(--msg-hover);
}

/* ===== 上传提示 ===== */
.upload-toast {
  position: absolute;
  top: 60px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--accent);
  color: #fff;
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 13px;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* ===== 消息区 ===== */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0;
  scroll-behavior: smooth;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px 20px;
  text-align: center;
}

.welcome-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  color: #fff;
}

.welcome h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.welcome-hint {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 28px;
}

.suggestions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

.suggestions button {
  padding: 10px 16px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s, background 0.2s;
}

.suggestions button:hover {
  border-color: var(--text-secondary);
  color: var(--text-primary);
  background: var(--msg-hover);
}

/* ===== 消息行 ===== */
.msg-row {
  display: flex;
  gap: 16px;
  padding: 20px 24px;
  max-width: 768px;
  margin: 0 auto;
  width: 100%;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.msg-row.assistant {
  background: var(--msg-hover);
  border-radius: 0;
  max-width: 100%;
  padding: 20px calc((100% - 768px) / 2 + 24px);
}

.avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
}

.msg-row.user .avatar {
  background: var(--user-avatar-bg);
  color: #fff;
}

.msg-row.assistant .avatar {
  background: var(--ai-avatar-bg);
  color: #fff;
}

.msg-body {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}

.msg-content {
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-primary);
}

.msg-content p {
  margin-bottom: 12px;
}

.msg-content p:last-child {
  margin-bottom: 0;
}

.msg-content code {
  background: rgba(255,255,255,0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Fira Code', 'Cascadia Code', monospace;
}

.msg-content pre {
  background: #0d0d0d;
  border: 1px solid var(--border-color);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}

.msg-content pre code {
  background: none;
  padding: 0;
  font-size: 13px;
  line-height: 1.5;
}

.msg-content ul, .msg-content ol {
  padding-left: 20px;
  margin-bottom: 12px;
}

.msg-content li {
  margin-bottom: 4px;
}

/* ===== 引用来源 ===== */
.msg-sources {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}

.msg-sources summary {
  font-size: 12px;
  color: var(--accent);
  cursor: pointer;
  user-select: none;
}

.msg-sources ul {
  margin-top: 6px;
  padding-left: 16px;
  list-style: disc;
}

.msg-sources li {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 2px;
}

/* ===== 思考动画 ===== */
.thinking-indicator {
  display: flex;
  gap: 5px;
  padding: 4px 0;
}

.thinking-indicator span {
  width: 8px;
  height: 8px;
  background: var(--text-tertiary);
  border-radius: 50%;
  animation: pulse 1.4s infinite ease-in-out;
}

.thinking-indicator span:nth-child(2) { animation-delay: 0.2s; }
.thinking-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* ===== 输入区 ===== */
.input-wrapper {
  padding: 16px 24px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.input-box {
  display: flex;
  align-items: flex-end;
  width: 100%;
  max-width: 768px;
  background: var(--input-bg);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 10px 12px 10px 18px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-box:focus-within {
  border-color: var(--text-tertiary);
  box-shadow: 0 0 0 2px rgba(16, 163, 127, 0.1);
}

.input-box textarea {
  flex: 1;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.5;
  resize: none;
  outline: none;
  max-height: 150px;
  font-family: inherit;
}

.input-box textarea::placeholder {
  color: var(--text-tertiary);
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.input-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ===== 滚动条 ===== */
.messages::-webkit-scrollbar {
  width: 6px;
}

.messages::-webkit-scrollbar-track {
  background: transparent;
}

.messages::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}

.sidebar-nav::-webkit-scrollbar {
  width: 4px;
}

.sidebar-nav::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 2px;
}
</style>
