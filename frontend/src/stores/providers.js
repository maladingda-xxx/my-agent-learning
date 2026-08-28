/**
 * 供应商和模型状态管理（纯 reactive，不引入 pinia）
 */
import { ref, computed } from 'vue'

const providers = ref([])
const models = ref([])
const selectedModel = ref(localStorage.getItem('selectedModel') || '')
const loading = ref(false)

async function fetchProviders() {
  try {
    const res = await fetch('/api/providers/full')
    const data = await res.json()
    providers.value = data.providers || []
  } catch (e) {
    console.error('获取供应商失败:', e)
  }
}

async function fetchModels() {
  try {
    const res = await fetch('/api/models')
    const data = await res.json()
    models.value = data.models || []
    // 如果当前选中模型不在列表中，选第一个
    if (models.value.length && !models.value.find(m => m.model === selectedModel.value)) {
      selectModel(models.value[0].model)
    }
  } catch (e) {
    console.error('获取模型列表失败:', e)
  }
}

function selectModel(model) {
  selectedModel.value = model
  localStorage.setItem('selectedModel', model)
}

async function addProvider(provider) {
  const res = await fetch('/api/providers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(provider),
  })
  const data = await res.json()
  await fetchProviders()
  await fetchModels()
  return data
}

async function updateProvider(id, provider) {
  const res = await fetch(`/api/providers/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(provider),
  })
  const data = await res.json()
  await fetchProviders()
  await fetchModels()
  return data
}

async function deleteProvider(id) {
  await fetch(`/api/providers/${id}`, { method: 'DELETE' })
  await fetchProviders()
  await fetchModels()
}

async function init() {
  loading.value = true
  await fetchProviders()
  await fetchModels()
  loading.value = false
}

export function useProviders() {
  return {
    providers,
    models,
    selectedModel,
    loading,
    fetchProviders,
    fetchModels,
    selectModel,
    addProvider,
    updateProvider,
    deleteProvider,
    init,
  }
}
