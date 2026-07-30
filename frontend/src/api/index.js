import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
})

// --- Claude 三組：當前選的組別（1/2/3），由 Dashboard 的下拉設定 ---
// 集中在此管理，讓每個 Claude 請求自動帶上 group，不用每處手動加。
let currentGroup = 1
export const setClaudeGroup = (g) => { currentGroup = g }
export const getClaudeGroup = () => currentGroup
const withGroup = (params = {}) => ({ ...params, group: currentGroup })

export const getUsers = () =>
  api.get('/users', { params: withGroup() })

export const getInactiveUsers = (params) =>
  api.get('/users/inactive', { params: withGroup(params) })

export const getSummary = (params) =>
  api.get('/stats/summary', { params: withGroup(params) })

export const getRanking = (params) =>
  api.get('/stats/ranking', { params: withGroup(params) })

export const getHourly = (params) =>
  api.get('/stats/hourly', { params: withGroup(params) })

export const getDepartmentCost = () =>
  api.get('/stats/department-cost', { params: withGroup() })

export const importData = (usersFile, conversationsFile) => {
  const formData = new FormData()
  formData.append('group', currentGroup)          // 匯入也帶當前組別
  formData.append('users', usersFile)
  formData.append('conversations', conversationsFile)
  return api.post('/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// --- Claude 名單 CRUD（改名 / 級聯全刪，自動帶當前 group）---
export const renameClaudeUser = (uuid, fullName) =>
  api.put(`/users/${encodeURIComponent(uuid)}`, { full_name: fullName }, { params: withGroup() })

export const deleteClaudeUser = (uuid) =>
  api.delete(`/users/${encodeURIComponent(uuid)}`, { params: withGroup() })

export const setClaudeUserDepartment = (uuid, department) =>
  api.put(`/users/${encodeURIComponent(uuid)}/department`, { department }, { params: withGroup() })

// --- 部門：上傳 employee Excel 批次填部門（一次處理全部三組，不帶 group）---
export const importDepartments = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/import/departments', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// --- CSV 修正：上傳 members-analytics CSV（修正 json 漏抓，手動、不進 cron）---
export const importMemberAnalytics = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/import/member-analytics', fd, {
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

// --- OpenAI 部門：上傳 employee Excel 批次填部門（單檔，對齊 Claude 的 importDepartments）---
export const importOpenAiDepartments = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/openai/import/departments', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}