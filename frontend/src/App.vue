<script setup>
import { ref, nextTick } from 'vue'
import { marked } from 'marked'

const messages = ref([])
const inputText = ref('')
const isLoading = ref(false)
const sessionId = ref(`session_${Date.now()}`)
const uploadStatus = ref('')

const chatContainer = ref(null)

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

  // 添加一个空的 assistant 消息，用于流式填充
  const assistantMsg = { role: 'assistant', content: '', sources: [] }
  messages.value.push(assistantMsg)

  try {
    const response = await fetch('/api/chat/rag/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        session_id: sessionId.value,
      }),
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // 保留不完整的最后一行

      for (const line of lines) {
        if (line.startsWith('event: meta')) {
          // 下一行是 data
          continue
        }
        if (line.startsWith('event: done')) {
          continue
        }
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') break

          // 尝试解析为元数据 JSON
          try {
            const parsed = JSON.parse(data)
            if (parsed.type === 'meta') {
              assistantMsg.sources = parsed.sources || []
              continue
            }
          } catch {
            // 不是 JSON，是普通文本 token
          }

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
    const res = await fetch('/api/upload/', {
      method: 'POST',
      body: formData,
    })
    const result = await res.json()
    if (res.ok) {
      uploadStatus.value = `上传成功: ${file.name} (${result.chunks_stored || '?'} 个片段)`
    } else {
      uploadStatus.value = `上传失败: ${result.detail || '未知错误'}`
    }
  } catch (err) {
    uploadStatus.value = `上传失败: ${err.message}`
  }

  // 3 秒后清除状态
  setTimeout(() => { uploadStatus.value = '' }, 3000)
  event.target.value = '' // 允许重复上传同一文件
}

async function clearSession() {
  try {
    await fetch(`/api/session/${sessionId.value}`, { method: 'DELETE' })
  } catch {}
  messages.value = []
}
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>AI Agent Chat</h1>
      <div class="header-actions">
        <label class="upload-btn">
          上传文档
          <input type="file" accept=".pdf,.txt,.md" @change="handleFileSelect" hidden />
        </label>
        <button class="clear-btn" @click="clearSession">清空对话</button>
      </div>
    </header>

    <div class="chat-container" ref="chatContainer">
      <div v-if="messages.length === 0" class="empty-state">
        <p>你好！我是 AI 助手，可以回答问题或基于上传的文档进行问答。</p>
        <p class="hint">支持上传 PDF / TXT / Markdown 文件作为知识库</p>
      </div>

      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="message"
        :class="msg.role"
      >
        <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
        <div v-if="msg.sources && msg.sources.length" class="sources">
          <details>
            <summary>参考来源 ({{ msg.sources.length }})</summary>
            <ul>
              <li v-for="(s, i) in msg.sources" :key="i">
                {{ s.source || '未知来源' }}
                <span v-if="s.page"> - 第{{ s.page }}页</span>
              </li>
            </ul>
          </details>
        </div>
      </div>

      <div v-if="isLoading" class="message assistant">
        <div class="message-content typing">
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
      </div>
    </div>

    <div v-if="uploadStatus" class="upload-status">{{ uploadStatus }}</div>

    <form class="input-area" @submit.prevent="sendMessage">
      <input
        v-model="inputText"
        type="text"
        placeholder="输入消息..."
        :disabled="isLoading"
        autocomplete="off"
      />
      <button type="submit" :disabled="isLoading || !inputText.trim()">发送</button>
    </form>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  height: 100vh;
  overflow: hidden;
}

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 900px;
  margin: 0 auto;
  background: #fff;
  box-shadow: 0 0 20px rgba(0,0,0,0.05);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #e8e8e8;
  background: #fff;
}

.header h1 {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.upload-btn, .clear-btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid #d9d9d9;
  background: #fff;
  color: #555;
  transition: all 0.2s;
}

.upload-btn:hover, .clear-btn:hover {
  border-color: #4f46e5;
  color: #4f46e5;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  text-align: center;
  color: #888;
  margin-top: 30vh;
  line-height: 1.8;
}

.empty-state .hint {
  font-size: 13px;
  color: #aaa;
}

.message {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
  word-wrap: break-word;
}

.message.user {
  align-self: flex-end;
  background: #4f46e5;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message.assistant {
  align-self: flex-start;
  background: #f0f0f0;
  color: #1a1a1a;
  border-bottom-left-radius: 4px;
}

.message-content p {
  margin-bottom: 8px;
}

.message-content p:last-child {
  margin-bottom: 0;
}

.message-content code {
  background: rgba(0,0,0,0.06);
  padding: 2px 5px;
  border-radius: 3px;
  font-size: 13px;
}

.message-content pre {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-content pre code {
  background: none;
  padding: 0;
  color: inherit;
}

.sources {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}

.sources summary {
  cursor: pointer;
  color: #4f46e5;
}

.sources ul {
  margin-top: 4px;
  padding-left: 16px;
}

.typing {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.dot {
  width: 8px;
  height: 8px;
  background: #999;
  border-radius: 50%;
  animation: bounce 1.2s infinite;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

.upload-status {
  padding: 8px 24px;
  font-size: 13px;
  color: #4f46e5;
  background: #f8f7ff;
  border-top: 1px solid #e8e8e8;
}

.input-area {
  display: flex;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid #e8e8e8;
  background: #fff;
}

.input-area input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.input-area input:focus {
  border-color: #4f46e5;
}

.input-area button {
  padding: 10px 20px;
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.input-area button:hover:not(:disabled) {
  background: #4338ca;
}

.input-area button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
