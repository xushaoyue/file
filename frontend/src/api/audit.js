import api from './index'

export const fetchLogs = (params) => {
  return api.get('/audit/logs', { params })
}

export const fetchStats = () => {
  return api.get('/audit/stats')
}

export const exportLogs = (params) => {
  return api.get('/audit/export', { params, responseType: 'blob' })
}

export const fetchLogDetail = (id) => {
  return api.get(`/audit/logs/${id}`)
}

export const clearOldLogs = (days) => {
  return api.delete('/audit/clear', { data: { days } })
}
