import axios from 'axios'

const API_BASE = '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth
export const login = (username, password) =>
  api.post('/auth/login', { username, password })

// Dashboard
export const getOverview = () => api.get('/analytics/overview')
export const getEngagementTrends = (weeks = 12) =>
  api.get(`/analytics/engagement-trends?weeks=${weeks}`)
export const getDangerAlerts = (limit = 50) =>
  api.get(`/analytics/danger-alerts?limit=${limit}`)

// Users
export const getUsers = (params = {}) => api.get('/users', { params })
export const getUser = (id) => api.get(`/users/${id}`)
export const updateUser = (id, data) => api.patch(`/users/${id}`, data)
export const deactivateUser = (id) => api.post(`/users/${id}/deactivate`)

// Conversations
export const getConversations = (params = {}) =>
  api.get('/conversations', { params })

// Exports
export const exportConversations = (studyGroup) => {
  const params = studyGroup ? `?study_group=${studyGroup}` : ''
  return api.get(`/analytics/export/conversations${params}`, {
    responseType: 'blob',
  })
}
export const exportEngagement = () =>
  api.get('/analytics/export/engagement', { responseType: 'blob' })
export const exportAssessments = () =>
  api.get('/analytics/export/assessments', { responseType: 'blob' })

export default api
