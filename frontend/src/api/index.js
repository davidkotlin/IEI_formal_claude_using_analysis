import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
})

export const getUsers = () =>
  api.get('/api/users')

export const getInactiveUsers = (params) =>
  api.get('/api/users/inactive', { params })

export const getSummary = (params) =>
  api.get('/api/stats/summary', { params })

export const getRanking = (params) =>
  api.get('/api/stats/ranking', { params })

export const getHourly = (params) =>
  api.get('/api/stats/hourly', { params })

export const importData = (usersFile, conversationsFile) => {
  const formData = new FormData()
  formData.append('users', usersFile)
  formData.append('conversations', conversationsFile)
  return api.post('/api/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
