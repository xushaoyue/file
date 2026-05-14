<template>
  <el-container class="layout-container">
    <LayoutSidebar />
    <el-container>
      <LayoutHeader />
      <el-main class="main-content">
        <div class="dashboard">
          <h1 class="page-title">仪表盘</h1>
          
          <el-row :gutter="20" class="stats-row">
            <el-col :xs="24" :sm="12" :md="6">
              <el-card class="stat-card">
                <div class="stat-content">
                  <div class="stat-icon" style="background: #409eff;">
                    <el-icon :size="30"><Document /></el-icon>
                  </div>
                  <div class="stat-info">
                    <div class="stat-value">{{ stats.totalOperations || 0 }}</div>
                    <div class="stat-label">总操作数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            
            <el-col :xs="24" :sm="12" :md="6">
              <el-card class="stat-card">
                <div class="stat-content">
                  <div class="stat-icon" style="background: #67c23a;">
                    <el-icon :size="30"><TrendCharts /></el-icon>
                  </div>
                  <div class="stat-info">
                    <div class="stat-value">{{ stats.todayOperations || 0 }}</div>
                    <div class="stat-label">今日操作</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            
            <el-col :xs="24" :sm="12" :md="6">
              <el-card class="stat-card">
                <div class="stat-content">
                  <div class="stat-icon" style="background: #e6a23c;">
                    <el-icon :size="30"><User /></el-icon>
                  </div>
                  <div class="stat-info">
                    <div class="stat-value">{{ stats.activeUsers || 0 }}</div>
                    <div class="stat-label">活跃用户</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            
            <el-col :xs="24" :sm="12" :md="6">
              <el-card class="stat-card">
                <div class="stat-content">
                  <div class="stat-icon" style="background: #f56c6c;">
                    <el-icon :size="30"><Warning /></el-icon>
                  </div>
                  <div class="stat-info">
                    <div class="stat-value">{{ stats.failedOperations || 0 }}</div>
                    <div class="stat-label">失败操作</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
          
          <el-row :gutter="20">
            <el-col :xs="24" :md="16">
              <el-card class="recent-logs-card">
                <template #header>
                  <div class="card-header">
                    <span>最近审计日志</span>
                    <el-button type="primary" link @click="$router.push('/audit')">
                      查看更多
                    </el-button>
                  </div>
                </template>
                
                <el-table
                  :data="recentLogs"
                  :loading="loading"
                  style="width: 100%"
                >
                  <el-table-column prop="username" label="用户" width="120" />
                  <el-table-column prop="operation" label="操作" width="150" />
                  <el-table-column prop="resource" label="资源" />
                  <el-table-column prop="status" label="状态" width="100">
                    <template #default="{ row }">
                      <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
                        {{ row.status === 'success' ? '成功' : '失败' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="created_at" label="时间" width="180">
                    <template #default="{ row }">
                      {{ formatTime(row.created_at) }}
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>
            
            <el-col :xs="24" :md="8">
              <el-card class="quick-links-card">
                <template #header>
                  <span>快捷操作</span>
                </template>
                
                <div class="quick-links">
                  <el-button type="primary" class="quick-link-btn" @click="$router.push('/files')">
                    <el-icon><Folder /></el-icon>
                    文件浏览
                  </el-button>
                  <el-button type="success" class="quick-link-btn" @click="$router.push('/audit')">
                    <el-icon><List /></el-icon>
                    审计日志
                  </el-button>
                  <el-button type="warning" class="quick-link-btn" @click="$router.push('/settings')">
                    <el-icon><Setting /></el-icon>
                    系统设置
                  </el-button>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuditStore } from '@/stores/audit'
import LayoutSidebar from '@/components/Layout/Sidebar.vue'
import LayoutHeader from '@/components/Layout/Header.vue'
import { Document, TrendCharts, User, Warning, Folder, List, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const auditStore = useAuditStore()

const stats = ref({
  totalOperations: 0,
  todayOperations: 0,
  activeUsers: 0,
  failedOperations: 0
})
const recentLogs = ref([])
const loading = ref(false)

onMounted(async () => {
  await loadData()
})

const loadData = async () => {
  loading.value = true
  try {
    await Promise.all([
      fetchStats(),
      fetchRecentLogs()
    ])
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  try {
    const response = await auditStore.fetchStats()
    if (response) {
      stats.value = {
        totalOperations: response.total_operations || 0,
        todayOperations: response.today_operations || 0,
        activeUsers: response.active_users || 0,
        failedOperations: response.failed_operations || 0
      }
    }
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

const fetchRecentLogs = async () => {
  try {
    await auditStore.fetchLogs(1)
    recentLogs.value = (auditStore.logs || []).slice(0, 5)
  } catch (error) {
    console.error('获取最近日志失败:', error)
  }
}

const formatTime = (time) => {
  if (!time) return ''
  return new Date(time).toLocaleString('zh-CN')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.main-content {
  background: #f0f2f5;
  padding: 20px;
}

.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  margin-bottom: 20px;
  font-size: 24px;
  color: #333;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  height: 100%;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 10px;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 5px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.recent-logs-card {
  margin-bottom: 20px;
}

.quick-links-card {
  height: 100%;
}

.quick-links {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.quick-link-btn {
  width: 100%;
  justify-content: flex-start;
}
</style>
