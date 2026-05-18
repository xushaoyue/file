<template>
  <el-container class="layout-container" direction="vertical">
    <LayoutHeader />
    <el-container class="layout-body">
      <LayoutSidebar />
      <el-main class="main-content">
        <div class="file-browser">
          <div class="toolbar">
            <el-button type="primary" @click="handleRefresh">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button @click="handleNewFolder">
              <el-icon><FolderAdd /></el-icon>
              新建文件夹
            </el-button>
            <el-button @click="handleUpload">
              <el-icon><Upload /></el-icon>
              上传文件
            </el-button>
            <el-button type="danger" :disabled="!selectedFile" @click="handleDelete">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
          
          <div class="content-area">
            <el-aside width="250px" class="directory-tree">
              <el-card>
                <template #header>
                  <span>目录树</span>
                </template>
                <el-tree
                  :data="directoryTree"
                  :props="treeProps"
                  node-key="path"
                  :expand-on-click-node="false"
                  @node-click="handleNodeClick"
                  :load="loadTreeNode"
                  lazy
                >
                  <template #default="{ node, data }">
                    <span class="tree-node">
                      <el-icon v-if="data.is_directory"><Folder /></el-icon>
                      <el-icon v-else><Document /></el-icon>
                      <span>{{ node.label }}</span>
                    </span>
                  </template>
                </el-tree>
              </el-card>
            </el-aside>
            
            <div class="file-list-area">
              <el-breadcrumb separator="/">
                <el-breadcrumb-item
                  v-for="item in breadcrumb"
                  :key="item.path"
                >
                  <span class="breadcrumb-link" @click="loadFiles(item.path)">{{ item.name }}</span>
                </el-breadcrumb-item>
              </el-breadcrumb>
              
              <el-table
                ref="tableRef"
                :data="files"
                style="width: 100%; margin-top: 15px;"
                @selection-change="handleSelectionChange"
                @row-dblclick="handleRowDoubleClick"
              >
                <el-table-column type="selection" width="55" />
                <el-table-column label="名称" prop="name">
                  <template #default="{ row }">
                    <div class="file-name-cell">
                      <el-icon v-if="row.is_directory" color="#f0ad4e"><Folder /></el-icon>
                      <el-icon v-else color="#909399"><Document /></el-icon>
                      <span>{{ row.name }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="大小" width="120" prop="size">
                  <template #default="{ row }">
                    {{ row.is_directory ? '-' : formatSize(row.size) }}
                  </template>
                </el-table-column>
                <el-table-column label="修改时间" width="180" prop="modified_at">
                  <template #default="{ row }">
                    {{ formatTime(row.modified_at) }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="280">
                  <template #default="{ row }">
                    <el-button type="primary" link @click="handleView(row)">查看</el-button>
                    <el-button type="primary" link @click="handleDownload(row)" :disabled="row.is_directory">下载</el-button>
                    <el-button type="primary" link @click="handleRename(row)">重命名</el-button>
                    <el-button type="danger" link @click="handleDeleteFile(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
        
        <el-dialog v-model="previewVisible" title="文件预览" width="80%">
          <div class="file-preview">
            <el-input
              v-if="currentFile?.is_directory === false"
              v-model="fileContent"
              type="textarea"
              :rows="20"
              readonly
            />
            <div v-else class="folder-preview">
              <el-icon :size="60" color="#f0ad4e"><Folder /></el-icon>
              <p>这是一个文件夹</p>
            </div>
          </div>
        </el-dialog>
        
        <el-dialog v-model="uploadVisible" title="上传文件" width="400px">
          <el-upload
            ref="uploadRef"
            drag
            :action="uploadUrl"
            :headers="{ Authorization: `Bearer ${token}` }"
            :data="{ path: currentPath }"
            :auto-upload="false"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            multiple
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处或 <em>点击上传</em></div>
          </el-upload>
          <template #footer>
            <el-button @click="uploadVisible = false">取消</el-button>
            <el-button type="primary" @click="handleUploadConfirm">上传</el-button>
          </template>
        </el-dialog>
        
        <el-dialog v-model="newFolderVisible" title="新建文件夹" width="400px">
          <el-form @submit.prevent="handleCreateFolder">
            <el-form-item label="文件夹名称">
              <el-input v-model="newFolderName" placeholder="请输入文件夹名称" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="newFolderVisible = false">取消</el-button>
            <el-button type="primary" @click="handleCreateFolder">创建</el-button>
          </template>
        </el-dialog>
        
        <el-dialog v-model="renameVisible" title="重命名" width="400px">
          <el-form @submit.prevent="handleRenameConfirm">
            <el-form-item label="新名称">
              <el-input v-model="newFileName" placeholder="请输入新名称" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="renameVisible = false">取消</el-button>
            <el-button type="primary" @click="handleRenameConfirm">确定</el-button>
          </template>
        </el-dialog>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import * as filesApi from '@/api/files'
import LayoutSidebar from '@/components/Layout/Sidebar.vue'
import LayoutHeader from '@/components/Layout/Header.vue'
import { Folder, Document, Refresh, FolderAdd, Upload, Delete, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const token = computed(() => authStore.token)

const uploadUrl = '/api/v1/files/upload'

const tableRef = ref(null)
const uploadRef = ref(null)

const directoryTree = ref([])
const files = ref([])
const currentPath = ref('/')
const breadcrumb = ref([{ name: '根目录', path: '/' }])
const selectedFile = ref(null)
const selectedFiles = ref([])

const previewVisible = ref(false)
const uploadVisible = ref(false)
const newFolderVisible = ref(false)
const renameVisible = ref(false)

const currentFile = ref(null)
const fileContent = ref('')
const newFolderName = ref('')
const newFileName = ref('')

const treeProps = {
  label: 'name',
  children: 'children',
  isLeaf: 'is_leaf'
}

onMounted(() => {
  loadRootDirectory()
})

const mapFileItem = (item) => ({
  name: item.name,
  path: item.path,
  is_directory: item.type === 'directory',
  size: item.size,
  modified_at: item.modified_at
})

const loadRootDirectory = async () => {
  try {
    const response = await filesApi.fetchDirectoryTree('/')
    const data = response.data
    if (data && data.items) {
      directoryTree.value = data.items.filter(i => i.type === 'directory').map(mapFileItem)
    }
    await loadFiles('/')
  } catch (error) {
    ElMessage.error('加载目录失败')
  }
}

const loadFiles = async (path) => {
  try {
    const response = await filesApi.fetchFiles({ path })
    const data = response.data
    files.value = data && data.items ? data.items.map(mapFileItem) : []
    currentPath.value = path
    updateBreadcrumb(path)
  } catch (error) {
    ElMessage.error('加载文件列表失败')
  }
}

const loadTreeNode = async (node, resolve) => {
  if (node.level === 0) return resolve([])

  try {
    const response = await filesApi.fetchDirectoryTree(node.data.path)
    const data = response.data
    const items = data && data.items ? data.items : []
    const dirs = items.filter(i => i.type === 'directory').map(mapFileItem)
    resolve(dirs)
  } catch (error) {
    resolve([])
  }
}

const handleNodeClick = (data) => {
  if (data.is_directory) {
    loadFiles(data.path)
  }
}

const handleRowDoubleClick = (row) => {
  if (row.is_directory) {
    loadFiles(row.path)
  } else {
    handleView(row)
  }
}

const handleSelectionChange = (selection) => {
  selectedFiles.value = selection
  selectedFile.value = selection.length === 1 ? selection[0] : null
}

const handleRefresh = () => {
  loadFiles(currentPath.value)
}

const handleNewFolder = () => {
  newFolderName.value = ''
  newFolderVisible.value = true
}

const handleCreateFolder = async () => {
  if (!newFolderName.value.trim()) {
    ElMessage.warning('请输入文件夹名称')
    return
  }
  
  try {
    await filesApi.createDirectory(currentPath.value, newFolderName.value)
    ElMessage.success('创建成功')
    newFolderVisible.value = false
    loadFiles(currentPath.value)
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

const handleUpload = () => {
  uploadVisible.value = true
}

const handleUploadConfirm = () => {
  uploadRef.value?.submit()
}

const handleUploadSuccess = () => {
  ElMessage.success('上传成功')
  uploadVisible.value = false
  loadFiles(currentPath.value)
}

const handleUploadError = () => {
  ElMessage.error('上传失败')
}

const handleView = async (row) => {
  currentFile.value = row
  if (row.is_directory) {
    previewVisible.value = true
    return
  }
  
  try {
    const response = await filesApi.fetchFileContent(row.path)
    fileContent.value = response.data.content || ''
    previewVisible.value = true
  } catch (error) {
    ElMessage.error('加载文件内容失败')
  }
}

const handleRename = (row) => {
  currentFile.value = row
  newFileName.value = row.name
  renameVisible.value = true
}

const handleRenameConfirm = async () => {
  if (!newFileName.value.trim()) {
    ElMessage.warning('请输入新名称')
    return
  }
  
  try {
    const parentPath = currentFile.value.path.substring(0, currentFile.value.path.lastIndexOf('/'))
    const newPath = parentPath + '/' + newFileName.value
    await filesApi.renameFile(currentFile.value.path, newPath)
    ElMessage.success('重命名成功')
    renameVisible.value = false
    loadFiles(currentPath.value)
  } catch (error) {
    ElMessage.error('重命名失败')
  }
}

const handleDownload = async (row) => {
  try {
    const response = await filesApi.downloadFile(row.path)
    const blob = new Blob([response.data])
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = row.name
    link.click()
    URL.revokeObjectURL(link.href)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const handleDeleteFile = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除此文件吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await filesApi.deleteFile(row.path)
    ElMessage.success('删除成功')
    loadFiles(currentPath.value)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleDelete = async () => {
  if (selectedFiles.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedFiles.value.length} 个文件吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    for (const file of selectedFiles.value) {
      await filesApi.deleteFile(file.path)
    }
    ElMessage.success('删除成功')
    loadFiles(currentPath.value)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const updateBreadcrumb = (path) => {
  const parts = path.split('/').filter(p => p)
  breadcrumb.value = [{ name: '根目录', path: '/' }]
  
  let current = ''
  for (const part of parts) {
    current += '/' + part
    breadcrumb.value.push({ name: part, path: current })
  }
}

const formatSize = (bytes) => {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
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

.layout-body {
  flex: 1;
  overflow: hidden;
}

.main-content {
  background: #f0f2f5;
  padding: 20px;
}

.file-browser {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.toolbar {
  margin-bottom: 15px;
  display: flex;
  gap: 10px;
}

.content-area {
  display: flex;
  gap: 15px;
  flex: 1;
  overflow: hidden;
}

.directory-tree {
  flex-shrink: 0;
}

.file-list-area {
  flex: 1;
  overflow: auto;
  background: white;
  padding: 15px;
  border-radius: 4px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 5px;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-preview {
  min-height: 400px;
}

.folder-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.breadcrumb-link {
  cursor: pointer;
  color: #409eff;
}

.breadcrumb-link:hover {
  text-decoration: underline;
}
</style>
