<template>
  <el-container class="layout-container">
    <LayoutSidebar />
    <el-container>
      <LayoutHeader />
      <el-main class="main-content">
        <div class="settings">
          <h1 class="page-title">系统设置</h1>
          
          <el-row :gutter="20">
            <el-col :xs="24" :md="12">
              <el-card class="settings-card">
                <template #header>
                  <span>基本信息</span>
                </template>
                
                <el-form
                  ref="basicFormRef"
                  :model="basicForm"
                  label-width="100px"
                >
                  <el-form-item label="系统名称">
                    <el-input v-model="basicForm.systemName" />
                  </el-form-item>
                  
                  <el-form-item label="系统描述">
                    <el-input
                      v-model="basicForm.description"
                      type="textarea"
                      :rows="3"
                    />
                  </el-form-item>
                  
                  <el-form-item label="联系方式">
                    <el-input v-model="basicForm.contact" />
                  </el-form-item>
                  
                  <el-form-item>
                    <el-button type="primary" @click="handleSaveBasic">
                      保存设置
                    </el-button>
                  </el-form-item>
                </el-form>
              </el-card>
            </el-col>
            
            <el-col :xs="24" :md="12">
              <el-card class="settings-card">
                <template #header>
                  <span>审计设置</span>
                </template>
                
                <el-form
                  ref="auditFormRef"
                  :model="auditForm"
                  label-width="100px"
                >
                  <el-form-item label="日志保留">
                    <el-input-number
                      v-model="auditForm.logRetention"
                      :min="1"
                      :max="365"
                    />
                    <span style="margin-left: 10px;">天</span>
                  </el-form-item>
                  
                  <el-form-item label="日志等级">
                    <el-select v-model="auditForm.logLevel">
                      <el-option label="DEBUG" value="debug" />
                      <el-option label="INFO" value="info" />
                      <el-option label="WARNING" value="warning" />
                      <el-option label="ERROR" value="error" />
                    </el-select>
                  </el-form-item>
                  
                  <el-form-item label="启用审计">
                    <el-switch v-model="auditForm.enableAudit" />
                  </el-form-item>
                  
                  <el-form-item>
                    <el-button type="primary" @click="handleSaveAudit">
                      保存设置
                    </el-button>
                  </el-form-item>
                </el-form>
              </el-card>
            </el-col>
          </el-row>
          
          <el-row :gutter="20">
            <el-col :xs="24" :md="12">
              <el-card class="settings-card">
                <template #header>
                  <span>安全设置</span>
                </template>
                
                <el-form
                  ref="securityFormRef"
                  :model="securityForm"
                  label-width="100px"
                >
                  <el-form-item label="会话超时">
                    <el-input-number
                      v-model="securityForm.sessionTimeout"
                      :min="5"
                      :max="1440"
                    />
                    <span style="margin-left: 10px;">分钟</span>
                  </el-form-item>
                  
                  <el-form-item label="密码长度">
                    <el-input-number
                      v-model="securityForm.minPasswordLength"
                      :min="6"
                      :max="32"
                    />
                    <span style="margin-left: 10px;">位</span>
                  </el-form-item>
                  
                  <el-form-item label="强制双因素">
                    <el-switch v-model="securityForm.forceTwoFactor" />
                  </el-form-item>
                  
                  <el-form-item label="IP白名单">
                    <el-input
                      v-model="securityForm.ipWhitelist"
                      type="textarea"
                      :rows="3"
                      placeholder="每行一个IP地址"
                    />
                  </el-form-item>
                  
                  <el-form-item>
                    <el-button type="primary" @click="handleSaveSecurity">
                      保存设置
                    </el-button>
                  </el-form-item>
                </el-form>
              </el-card>
            </el-col>
            
            <el-col :xs="24" :md="12">
              <el-card class="settings-card">
                <template #header>
                  <span>文件设置</span>
                </template>
                
                <el-form
                  ref="fileFormRef"
                  :model="fileForm"
                  label-width="100px"
                >
                  <el-form-item label="最大上传">
                    <el-input-number
                      v-model="fileForm.maxUploadSize"
                      :min="1"
                      :max="500"
                    />
                    <span style="margin-left: 10px;">MB</span>
                  </el-form-item>
                  
                  <el-form-item label="允许类型">
                    <el-select
                      v-model="fileForm.allowedTypes"
                      multiple
                      placeholder="选择允许的文件类型"
                    >
                      <el-option label=".py" value=".py" />
                      <el-option label=".js" value=".js" />
                      <el-option label=".java" value=".java" />
                      <el-option label=".cpp" value=".cpp" />
                      <el-option label=".c" value=".c" />
                      <el-option label=".go" value=".go" />
                      <el-option label=".rs" value=".rs" />
                      <el-option label=".txt" value=".txt" />
                    </el-select>
                  </el-form-item>
                  
                  <el-form-item label="版本控制">
                    <el-switch v-model="fileForm.enableVersioning" />
                  </el-form-item>
                  
                  <el-form-item>
                    <el-button type="primary" @click="handleSaveFile">
                      保存设置
                    </el-button>
                  </el-form-item>
                </el-form>
              </el-card>
            </el-col>
          </el-row>
          
          <el-card class="danger-zone">
            <template #header>
              <span>危险操作</span>
            </template>
            
            <el-space direction="vertical" :size="20" style="width: 100%;">
              <div class="danger-item">
                <div class="danger-info">
                  <h4>清理审计日志</h4>
                  <p>删除指定天数之前的审计日志，此操作不可恢复</p>
                </div>
                <el-button type="danger" @click="handleClearLogs">
                  清理日志
                </el-button>
              </div>
              
              <el-divider />
              
              <div class="danger-item">
                <div class="danger-info">
                  <h4>导出系统配置</h4>
                  <p>导出所有系统配置为JSON文件</p>
                </div>
                <el-button type="warning" @click="handleExportConfig">
                  导出配置
                </el-button>
              </div>
              
              <el-divider />
              
              <div class="danger-item">
                <div class="danger-info">
                  <h4>系统重置</h4>
                  <p>重置所有系统设置为默认值，此操作不可恢复</p>
                </div>
                <el-button type="danger" @click="handleResetSystem">
                  重置系统
                </el-button>
              </div>
            </el-space>
          </el-card>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, reactive } from 'vue'
import LayoutSidebar from '@/components/Layout/Sidebar.vue'
import LayoutHeader from '@/components/Layout/Header.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const basicFormRef = ref(null)
const auditFormRef = ref(null)
const securityFormRef = ref(null)
const fileFormRef = ref(null)

const basicForm = reactive({
  systemName: '源代码审计系统',
  description: '企业级源代码安全审计平台',
  contact: 'admin@example.com'
})

const auditForm = reactive({
  logRetention: 90,
  logLevel: 'info',
  enableAudit: true
})

const securityForm = reactive({
  sessionTimeout: 30,
  minPasswordLength: 8,
  forceTwoFactor: false,
  ipWhitelist: ''
})

const fileForm = reactive({
  maxUploadSize: 100,
  allowedTypes: ['.py', '.js', '.java', '.txt'],
  enableVersioning: true
})

const handleSaveBasic = () => {
  ElMessage.success('基本信息已保存')
}

const handleSaveAudit = () => {
  ElMessage.success('审计设置已保存')
}

const handleSaveSecurity = () => {
  ElMessage.success('安全设置已保存')
}

const handleSaveFile = () => {
  ElMessage.success('文件设置已保存')
}

const handleClearLogs = async () => {
  try {
    await ElMessageBox.confirm('确定要清理所有审计日志吗？此操作不可恢复！', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    ElMessage.success('日志清理完成')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清理失败')
    }
  }
}

const handleExportConfig = () => {
  const config = {
    basic: basicForm,
    audit: auditForm,
    security: securityForm,
    file: fileForm
  }
  
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `system_config_${Date.now()}.json`
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('配置已导出')
}

const handleResetSystem = async () => {
  try {
    await ElMessageBox.confirm('确定要重置所有系统设置吗？此操作不可恢复！', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'error'
    })
    
    ElMessage.success('系统已重置为默认值')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重置失败')
    }
  }
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

.settings {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  margin-bottom: 20px;
  font-size: 24px;
  color: #333;
}

.settings-card {
  margin-bottom: 20px;
}

.danger-zone {
  margin-top: 20px;
  border-color: #f56c6c;
}

.danger-zone :deep(.el-card__header) {
  color: #f56c6c;
}

.danger-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.danger-info h4 {
  margin: 0 0 5px 0;
  color: #333;
}

.danger-info p {
  margin: 0;
  color: #999;
  font-size: 14px;
}
</style>
