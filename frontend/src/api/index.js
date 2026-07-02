import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
})

export const getUsers = () =>
  api.get('/users')

export const getInactiveUsers = (params) =>
  api.get('/users/inactive', { params })

export const getSummary = (params) =>
  api.get('/stats/summary', { params })

export const getRanking = (params) =>
  api.get('/stats/ranking', { params })

export const getHourly = (params) =>
  api.get('/stats/hourly', { params })

export const importData = (usersFile, conversationsFile) => {
  const formData = new FormData()
  formData.append('users', usersFile)
  formData.append('conversations', conversationsFile)
  return api.post('/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// --- OpenAI 唯讀分析 ---
export const getOpenAiSummary  = (params) => api.get('/openai/stats/summary',  { params })
export const getOpenAiRanking  = (params) => api.get('/openai/stats/ranking',  { params })
export const getOpenAiInactive = (params) => api.get('/openai/stats/inactive', { params })
export const getOpenAiMatrix   = (params) => api.get('/openai/stats/matrix',   { params })

// --- OpenAI 名單 CRUD ---
export const getOpenAiUsers   = ()              => api.get('/openai/users')
export const createOpenAiUser = (body)          => api.post('/openai/users', body)
export const updateOpenAiUser = (email, body)   => api.put(`/openai/users/${encodeURIComponent(email)}`, body)
export const deleteOpenAiUser = (email, cascade) =>
  api.delete(`/openai/users/${encodeURIComponent(email)}`, { params: cascade ? { cascade: 1 } : {} })

// --- OpenAI 手動上傳（多檔）---
export const importOpenAiData = (files) => {
  const fd = new FormData()
  files.forEach((f) => fd.append('files', f))
  return api.post('/openai/import', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}