<template>
  <el-container class="layout-container" direction="vertical">
    <LayoutHeader />
    <el-container class="layout-body">
      <LayoutSidebar />
      <el-main class="main-content">
        <div class="audit-logs">
          <h1 class="page-title">审计日志</h1>
          
          <el-card class="filter-card">
            <el-form :inline="true" :model="filterForm" class="filter-form">
              <el-form-item label="日期范围">
                <el-date-picker
                  v-model="filterForm.dateRange"
                  type="daterange"
                  range-separator="至"
                  start-placeholder="开始日期"
                  end-placeholder="结束日期"
                  value-format="YYYY-MM-DD"
                  @change="handleFilterChange"
                />
              </el-form-item>
              
              <el-form-item label="用户名">
                <el-input
                  v-model="filterForm.username"
                  placeholder="请输入用户名"
                  clearable
                  @change="handleFilterChange"
                />
              </el-form-item>
              
              <el-form-item label="操作类型">
                <el-select
                  v-model="filterForm.operation"
                  placeholder="请选择"
                  clearable
                  @change="handleFilterChange"
                >
                  <el-option label="登录" value="login" />
                  <el-option label="登出" value="logout" />
                  <el-option label="查看" value="view" />
                  <el-option label="创建" value="create" />
                  <el-option label="修改" value="update" />
                  <el-option label="删除" value="delete" />
                  <el-option label="下载" value="download" />
                  <el-option label="上传" value="upload" />
                </el-select>
              </el-form-item>
              
              <el-form-item label="状态">
                <el-select
                  v-model="filterForm.status"
                  placeholder="请选择"
                  clearable
                  @change="handleFilterChange"
                >
                  <el-option label="成功" value="success" />
                  <el-option label="失败" value="failed" />
                </el-select>
              </el-form-item>
              
              <el-form-item>
                <el-button type="primary" @click="handleSearch">
                  <el-icon><Search /></el-icon>
                  搜索
                </el-button>
                <el-button @click="handleReset">
                  <el-icon><Refresh /></el-icon>
                  重置
                </el-button>
                <el-button type="success" @click="handleExport">
                  <el-icon><Download /></el-icon>
                  导出
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
          
          <el-row :gutter="20" class="stats-charts">
            <el-col :xs="24" :md="12">
              <el-card>
                <template #header>
                  <span>操作类型统计</span>
                </template>
                <div ref="operationChartRef" style="height: 300px;"></div>
              </el-card>
            </el-col>
            
            <el-col :xs="24" :md="12">
              <el-card>
                <template #header>
                  <span>每日操作趋势</span>
                </template>
                <div ref="trendChartRef" style="height: 300px;"></div>
              </el-card>
            </el-col>
          </el-row>
          
          <el-card class="logs-table-card">
            <el-table
              :data="logs"
              :loading="loading"
              style="width: 100%"
              stripe
            >
              <el-table-column type="index" label="序号" width="60" />
              <el-table-column prop="username" label="用户名" width="120" />
              <el-table-column prop="operation" label="操作" width="120">
                <template #default="{ row }">
                  <el-tag>{{ getOperationLabel(row.operation) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="file_path" label="资源" min-width="200" />
              <el-table-column prop="client_ip" label="IP地址" width="140" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
                    {{ row.status === 'success' ? '成功' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="详情" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  {{ row.error_message || row.diff_content || '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="timestamp" label="时间" width="180">
                <template #default="{ row }">
                  {{ formatTime(row.timestamp) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" link @click="handleViewDetail(row)">
                    详情
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            
            <div class="pagination-container">
              <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="[10, 20, 50, 100]"
                :total="total"
                layout="total, sizes, prev, pager, next, jumper"
                @size-change="handleSizeChange"
                @current-change="handlePageChange"
              />
            </div>
          </el-card>
        </div>
        
        <el-dialog v-model="detailVisible" title="日志详情" width="600px">
          <el-descriptions :column="2" border v-if="currentLog">
            <el-descriptions-item label="用户名">{{ currentLog.username }}</el-descriptions-item>
            <el-descriptions-item label="操作">
              <el-tag>{{ getOperationLabel(currentLog.operation) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="资源" :span="2">{{ currentLog.file_path }}</el-descriptions-item>
            <el-descriptions-item label="IP地址">{{ currentLog.client_ip }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="currentLog.status === 'success' ? 'success' : 'danger'">
                {{ currentLog.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="User-Agent" :span="2">{{ currentLog.user_agent }}</el-descriptions-item>
            <el-descriptions-item label="详情" :span="2">{{ currentLog.error_message || currentLog.diff_content || '-' }}</el-descriptions-item>
            <el-descriptions-item label="时间" :span="2">{{ formatTime(currentLog.timestamp) }}</el-descriptions-item>
          </el-descriptions>
        </el-dialog>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useAuditStore } from '@/stores/audit'
import LayoutSidebar from '@/components/Layout/Sidebar.vue'
import LayoutHeader from '@/components/Layout/Header.vue'
import { Search, Refresh, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const auditStore = useAuditStore()

const logs = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const filterForm = reactive({
  dateRange: [],
  username: '',
  operation: '',
  status: ''
})

const detailVisible = ref(false)
const currentLog = ref(null)

const operationChartRef = ref(null)
const trendChartRef = ref(null)

let operationChart = null
let trendChart = null

onMounted(() => {
  loadLogs()
  loadStats()
})

onUnmounted(() => {
  if (operationChart) operationChart.dispose()
  if (trendChart) trendChart.dispose()
})

const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (filterForm.dateRange && filterForm.dateRange.length === 2) {
      params.start_date = filterForm.dateRange[0]
      params.end_date = filterForm.dateRange[1]
    }
    
    if (filterForm.username) params.username = filterForm.username
    if (filterForm.operation) params.operation = filterForm.operation
    if (filterForm.status) params.status = filterForm.status
    
    const response = await auditStore.fetchLogs(currentPage.value)
    logs.value = auditStore.logs
    total.value = auditStore.total
  } catch (error) {
    ElMessage.error('加载日志失败')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    await auditStore.fetchStats()
    renderCharts()
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

const renderCharts = () => {
  if (typeof window !== 'undefined') {
    import('echarts').then((echarts) => {
      if (operationChartRef.value) {
        operationChart = echarts.init(operationChartRef.value)
        const stats = auditStore.statistics || {}
        const operationData = stats.operations_by_type || {}
        
        operationChart.setOption({
          tooltip: { trigger: 'item' },
          legend: { bottom: 0 },
          series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
            label: { show: false, position: 'center' },
            emphasis: { label: { show: true, fontSize: 20 } },
            labelLine: { show: false },
            data: Object.entries(operationData).map(([name, value]) => ({
              name: getOperationLabel(name),
              value
            }))
          }]
        })
      }
      
      if (trendChartRef.value) {
        trendChart = echarts.init(trendChartRef.value)
        const stats = auditStore.statistics || {}
        const trendData = stats.daily_trend || []
        
        trendChart.setOption({
          tooltip: { trigger: 'axis' },
          xAxis: {
            type: 'category',
            data: trendData.map(item => item.date)
          },
          yAxis: { type: 'value' },
          series: [{
            data: trendData.map(item => item.count),
            type: 'line',
            smooth: true,
            areaStyle: { opacity: 0.3 }
          }]
        })
      }
      
      window.addEventListener('resize', () => {
        operationChart?.resize()
        trendChart?.resize()
      })
    })
  }
}

const handleFilterChange = () => {
  handleSearch()
}

const handleSearch = () => {
  currentPage.value = 1
  auditStore.setFilters({
    start_date: filterForm.dateRange?.[0] || '',
    end_date: filterForm.dateRange?.[1] || '',
    username: filterForm.username,
    operation: filterForm.operation,
    status: filterForm.status
  })
  loadLogs()
}

const handleReset = () => {
  filterForm.dateRange = []
  filterForm.username = ''
  filterForm.operation = ''
  filterForm.status = ''
  auditStore.clearFilters()
  loadLogs()
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadLogs()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  loadLogs()
}

const handleExport = async () => {
  try {
    const blob = await auditStore.exportLogs('csv')
    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.download = `audit_logs_${Date.now()}.csv`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

const handleViewDetail = (row) => {
  currentLog.value = row
  detailVisible.value = true
}

const getOperationLabel = (operation) => {
  const labels = {
    login: '登录',
    logout: '登出',
    view: '查看',
    create: '创建',
    update: '修改',
    delete: '删除',
    download: '下载',
    upload: '上传'
  }
  return labels[operation] || operation
}

const formatTime = (time) => {
  if (!time) return '-'
  if (typeof time === 'string' && !time.endsWith('Z') && !time.includes('+')) {
    return new Date(time + 'Z').toLocaleString('zh-CN')
  }
  return new Date(time).toLocaleString('zh-CN')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.layout-body {
  flex: 1;
  overflow: hidden;
}

.main-content {
  background: #f0f2f5;
  padding: 20px;
}

.audit-logs {
  max-width: 1600px;
  margin: 0 auto;
}

.page-title {
  margin-bottom: 20px;
  font-size: 24px;
  color: #333;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stats-charts {
  margin-bottom: 20px;
}

.logs-table-card {
  margin-bottom: 20px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
