<template>
  <el-container class="layout-container">
    <LayoutSidebar />
    <el-container>
      <LayoutHeader />
      <el-main class="main-content">
        <div class="user-management">
          <h1 class="page-title">用户管理</h1>
          
          <el-card>
            <template #header>
              <div class="card-header">
                <span>用户列表</span>
                <el-button type="primary" @click="handleCreate">
                  <el-icon><Plus /></el-icon>
                  新建用户
                </el-button>
              </div>
            </template>
            
            <el-table
              :data="users"
              :loading="loading"
              style="width: 100%"
              stripe
            >
              <el-table-column type="index" label="序号" width="60" />
              <el-table-column prop="username" label="用户名" width="150" />
              <el-table-column prop="email" label="邮箱" width="200" />
              <el-table-column prop="full_name" label="姓名" width="120" />
              <el-table-column prop="role" label="角色" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'">
                    {{ row.role === 'admin' ? '管理员' : '普通用户' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="is_active" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.is_active ? 'success' : 'info'">
                    {{ row.is_active ? '启用' : '禁用' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="last_login" label="最后登录" width="180">
                <template #default="{ row }">
                  {{ formatTime(row.last_login) }}
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="创建时间" width="180">
                <template #default="{ row }">
                  {{ formatTime(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="250" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
                  <el-button type="warning" link @click="handlePermissions(row)">权限</el-button>
                  <el-button type="danger" link @click="handleResetPassword(row)">重置密码</el-button>
                  <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
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
        
        <el-dialog
          v-model="formVisible"
          :title="isEdit ? '编辑用户' : '新建用户'"
          width="500px"
        >
          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-width="80px"
          >
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" :disabled="isEdit" />
            </el-form-item>
            
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="form.email" type="email" />
            </el-form-item>
            
            <el-form-item label="姓名" prop="full_name">
              <el-input v-model="form.full_name" />
            </el-form-item>
            
            <el-form-item label="角色" prop="role">
              <el-select v-model="form.role">
                <el-option label="管理员" value="admin" />
                <el-option label="普通用户" value="user" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="状态">
              <el-switch v-model="form.is_active" />
            </el-form-item>
            
            <el-form-item v-if="!isEdit" label="密码" prop="password">
              <el-input v-model="form.password" type="password" show-password />
            </el-form-item>
          </el-form>
          
          <template #footer>
            <el-button @click="formVisible = false">取消</el-button>
            <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
              确定
            </el-button>
          </template>
        </el-dialog>
        
        <el-dialog v-model="permissionVisible" title="权限配置" width="600px">
          <el-form label-width="100px">
            <el-form-item label="用户">{{ currentUser?.username }}</el-form-item>
            <el-form-item label="权限配置">
              <el-tree
                ref="permissionTreeRef"
                :data="permissionTree"
                :props="treeProps"
                show-checkbox
                node-key="id"
                default-expand-all
              />
            </el-form-item>
          </el-form>
          
          <template #footer>
            <el-button @click="permissionVisible = false">取消</el-button>
            <el-button type="primary" :loading="submitLoading" @click="handlePermissionSubmit">
              确定
            </el-button>
          </template>
        </el-dialog>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import * as usersApi from '@/api/users'
import LayoutSidebar from '@/components/Layout/Sidebar.vue'
import LayoutHeader from '@/components/Layout/Header.vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const users = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const formVisible = ref(false)
const permissionVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)

const currentUser = ref(null)
const formRef = ref(null)
const permissionTreeRef = ref(null)

const form = reactive({
  username: '',
  email: '',
  full_name: '',
  role: 'user',
  is_active: true,
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

const permissionTree = ref([
  {
    id: 'files',
    label: '文件管理',
    children: [
      { id: 'files.view', label: '查看文件' },
      { id: 'files.create', label: '创建文件' },
      { id: 'files.edit', label: '编辑文件' },
      { id: 'files.delete', label: '删除文件' },
      { id: 'files.download', label: '下载文件' }
    ]
  },
  {
    id: 'audit',
    label: '审计日志',
    children: [
      { id: 'audit.view', label: '查看日志' },
      { id: 'audit.export', label: '导出日志' },
      { id: 'audit.delete', label: '删除日志' }
    ]
  },
  {
    id: 'users',
    label: '用户管理',
    children: [
      { id: 'users.view', label: '查看用户' },
      { id: 'users.create', label: '创建用户' },
      { id: 'users.edit', label: '编辑用户' },
      { id: 'users.delete', label: '删除用户' }
    ]
  },
  {
    id: 'settings',
    label: '系统设置',
    children: [
      { id: 'settings.view', label: '查看设置' },
      { id: 'settings.edit', label: '编辑设置' }
    ]
  }
])

const treeProps = {
  label: 'label',
  children: 'children'
}

onMounted(() => {
  loadUsers()
})

const loadUsers = async () => {
  loading.value = true
  try {
    const response = await usersApi.fetchUsers({
      page: currentPage.value,
      page_size: pageSize.value
    })
    users.value = response.data.items || response.data.results || response.data
    total.value = response.data.total || users.value.length
  } catch (error) {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  isEdit.value = false
  resetForm()
  formVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  currentUser.value = row
  Object.assign(form, {
    username: row.username,
    email: row.email,
    full_name: row.full_name || '',
    role: row.role,
    is_active: row.is_active,
    password: ''
  })
  formVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        if (isEdit.value) {
          await usersApi.updateUser(currentUser.value.id, form)
          ElMessage.success('更新成功')
        } else {
          await usersApi.createUser(form)
          ElMessage.success('创建成功')
        }
        formVisible.value = false
        loadUsers()
      } catch (error) {
        ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

const handlePermissions = (row) => {
  currentUser.value = row
  permissionVisible.value = true
}

const handlePermissionSubmit = async () => {
  if (!currentUser.value) return
  
  submitLoading.value = true
  try {
    const checkedKeys = permissionTreeRef.value?.getCheckedKeys() || []
    await usersApi.updatePermissions(currentUser.value.id, checkedKeys)
    ElMessage.success('权限配置成功')
    permissionVisible.value = false
  } catch (error) {
    ElMessage.error('权限配置失败')
  } finally {
    submitLoading.value = false
  }
}

const handleResetPassword = async (row) => {
  try {
    await ElMessageBox.confirm('确定要重置此用户的密码吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await usersApi.resetPassword(row.id)
    ElMessage.success('密码已重置为默认值')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重置密码失败')
    }
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除此用户吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await usersApi.deleteUser(row.id)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadUsers()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  loadUsers()
}

const resetForm = () => {
  Object.assign(form, {
    username: '',
    email: '',
    full_name: '',
    role: 'user',
    is_active: true,
    password: ''
  })
  formRef.value?.clearValidate()
}

const formatTime = (time) => {
  if (!time) return '-'
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

.user-management {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  margin-bottom: 20px;
  font-size: 24px;
  color: #333;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
