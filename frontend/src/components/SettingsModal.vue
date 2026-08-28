<script setup>
import { ref, onMounted } from 'vue'
import { useProviders } from '../stores/providers.js'

const emit = defineEmits(['close'])
const { providers, fetchProviders, addProvider, updateProvider, deleteProvider } = useProviders()

const editingProvider = ref(null)
const form = ref({ name: '', api_base: '', api_key: '', models: '' })

// 预设供应商模板
const presets = [
  { name: 'OpenAI', api_base: 'https://api.openai.com/v1', models: 'gpt-4o,gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo' },
  { name: 'DeepSeek', api_base: 'https://api.deepseek.com', models: 'deepseek-chat,deepseek-reasoner' },
  { name: 'Claude (via proxy)', api_base: 'https://api.anthropic.com/v1', models: 'claude-sonnet-4-20250514,claude-haiku-4-20250414' },
  { name: 'Moonshot', api_base: 'https://api.moonshot.cn/v1', models: 'moonshot-v1-8k,moonshot-v1-32k,moonshot-v1-128k' },
  { name: 'Qwen (通义千问)', api_base: 'https://dashscope.aliyuncs.com/compatible-mode/v1', models: 'qwen-turbo,qwen-plus,qwen-max' },
  { name: 'GLM (智谱)', api_base: 'https://open.bigmodel.cn/api/paas/v4', models: 'glm-4-flash,glm-4,glm-4-plus' },
]

function resetForm() {
  form.value = { name: '', api_base: '', api_key: '', models: '' }
  editingProvider.value = null
}

function applyPreset(preset) {
  form.value.name = preset.name
  form.value.api_base = preset.api_base
  form.value.models = preset.models
  form.value.api_key = ''
  editingProvider.value = null
}

function startEdit(provider) {
  editingProvider.value = provider.id
  form.value = {
    name: provider.name,
    api_base: provider.api_base,
    api_key: provider.api_key,
    models: provider.models.join(','),
  }
}

async function handleSave() {
  const payload = {
    name: form.value.name,
    api_base: form.value.api_base,
    api_key: form.value.api_key,
    models: form.value.models.split(',').map(s => s.trim()).filter(Boolean),
  }

  if (editingProvider.value) {
    await updateProvider(editingProvider.value, payload)
  } else {
    await addProvider(payload)
  }
  resetForm()
}

async function handleDelete(id) {
  await deleteProvider(id)
}

onMounted(() => {
  fetchProviders()
})
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>模型供应商设置</h2>
        <button class="close-btn" @click="emit('close')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <div class="modal-body">
        <!-- 已有供应商列表 -->
        <div class="section">
          <h3>已配置的供应商</h3>
          <div v-if="providers.length === 0" class="empty-hint">暂无供应商，请添加</div>
          <div v-for="p in providers" :key="p.id" class="provider-card">
            <div class="provider-info">
              <span class="provider-name">{{ p.name }}</span>
              <span class="provider-models">{{ p.models.join(', ') }}</span>
              <span class="provider-base">{{ p.api_base }}</span>
            </div>
            <div class="provider-actions">
              <button class="action-btn" @click="startEdit(p)">编辑</button>
              <button class="action-btn danger" @click="handleDelete(p.id)">删除</button>
            </div>
          </div>
        </div>

        <!-- 快速添加预设 -->
        <div class="section">
          <h3>快速添加</h3>
          <div class="presets">
            <button
              v-for="preset in presets"
              :key="preset.name"
              class="preset-btn"
              @click="applyPreset(preset)"
            >{{ preset.name }}</button>
          </div>
        </div>

        <!-- 表单 -->
        <div class="section">
          <h3>{{ editingProvider ? '编辑供应商' : '添加供应商' }}</h3>
          <form class="provider-form" @submit.prevent="handleSave">
            <div class="form-row">
              <label>名称</label>
              <input v-model="form.name" placeholder="如: OpenAI" required />
            </div>
            <div class="form-row">
              <label>API Base URL</label>
              <input v-model="form.api_base" placeholder="https://api.openai.com/v1" required />
            </div>
            <div class="form-row">
              <label>API Key</label>
              <input v-model="form.api_key" type="password" placeholder="sk-..." required />
            </div>
            <div class="form-row">
              <label>模型列表 (逗号分隔)</label>
              <input v-model="form.models" placeholder="gpt-4o, gpt-4o-mini" required />
            </div>
            <div class="form-buttons">
              <button type="button" class="cancel-btn" @click="resetForm" v-if="editingProvider">取消</button>
              <button type="submit" class="save-btn">{{ editingProvider ? '保存修改' : '添加' }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal {
  background: #1e1e1e;
  border: 1px solid #333;
  border-radius: 16px;
  width: 560px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #2e2e2e;
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: #ececec;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #9a9a9a;
  cursor: pointer;
}

.close-btn:hover {
  background: #2a2a2a;
  color: #fff;
}

.modal-body {
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section h3 {
  font-size: 14px;
  font-weight: 500;
  color: #9a9a9a;
  margin-bottom: 12px;
}

.empty-hint {
  font-size: 13px;
  color: #6b6b6b;
  padding: 8px 0;
}

/* 供应商卡片 */
.provider-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #262626;
  border: 1px solid #333;
  border-radius: 10px;
  margin-bottom: 8px;
}

.provider-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.provider-name {
  font-size: 14px;
  font-weight: 500;
  color: #ececec;
}

.provider-models {
  font-size: 12px;
  color: #10a37f;
}

.provider-base {
  font-size: 11px;
  color: #6b6b6b;
}

.provider-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid #444;
  border-radius: 6px;
  background: transparent;
  color: #9a9a9a;
  cursor: pointer;
  transition: all 0.15s;
}

.action-btn:hover {
  border-color: #666;
  color: #ececec;
}

.action-btn.danger:hover {
  border-color: #e53935;
  color: #e53935;
}

/* 预设按钮 */
.presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preset-btn {
  padding: 6px 14px;
  font-size: 13px;
  border: 1px solid #333;
  border-radius: 8px;
  background: transparent;
  color: #9a9a9a;
  cursor: pointer;
  transition: all 0.15s;
}

.preset-btn:hover {
  border-color: #10a37f;
  color: #10a37f;
  background: rgba(16,163,127,0.05);
}

/* 表单 */
.provider-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-row label {
  font-size: 12px;
  color: #9a9a9a;
}

.form-row input {
  padding: 8px 12px;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #ececec;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.form-row input:focus {
  border-color: #10a37f;
}

.form-row input::placeholder {
  color: #555;
}

.form-buttons {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 4px;
}

.save-btn {
  padding: 8px 18px;
  background: #10a37f;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.save-btn:hover {
  background: #0d8c6d;
}

.cancel-btn {
  padding: 8px 18px;
  background: transparent;
  color: #9a9a9a;
  border: 1px solid #444;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
}

.cancel-btn:hover {
  border-color: #666;
  color: #ececec;
}
</style>
