import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchLogs as apiFetchLogs, fetchStats as apiFetchStats, exportLogs as apiExportLogs } from '@/api/audit'

export const useAuditStore = defineStore('audit', () => {
  const logs = ref([])
  const statistics = ref(null)
  const filters = ref({
    startDate: '',
    endDate: '',
    username: '',
    operation: '',
    status: ''
  })
  const loading = ref(false)
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)

  async function fetchLogs(page = 1) {
    loading.value = true
    try {
      currentPage.value = page
      const params = {
        page,
        page_size: pageSize.value,
        ...filters.value
      }
      const response = await apiFetchLogs(params)
      logs.value = response.data.items || response.data.results || response.data
      total.value = response.data.total || logs.value.length
    } catch (error) {
      console.error('获取审计日志失败:', error)
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      const response = await apiFetchStats()
      statistics.value = response.data
    } catch (error) {
      console.error('获取统计数据失败:', error)
    }
  }

  async function exportLogs(format = 'csv') {
    try {
      const response = await apiExportLogs({ ...filters.value, format })
      return response.data
    } catch (error) {
      console.error('导出审计日志失败:', error)
      throw error
    }
  }

  function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
  }

  function clearFilters() {
    filters.value = {
      startDate: '',
      endDate: '',
      username: '',
      operation: '',
      status: ''
    }
  }

  return {
    logs,
    statistics,
    filters,
    loading,
    total,
    currentPage,
    pageSize,
    fetchLogs,
    fetchStats,
    exportLogs,
    setFilters,
    clearFilters
  }
})
