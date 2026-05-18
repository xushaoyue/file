<template>
  <el-container class="layout-container" direction="vertical">
    <LayoutHeader />
    <el-container class="layout-body">
      <LayoutSidebar />
      <el-main class="main-content">
        <div class="page-container">
          <div class="page-header">
            <h1 class="page-title">Git 仓库管理</h1>
            <el-button type="primary" @click="showCreateModal = true">
              <el-icon><Plus /></el-icon>
              添加仓库
            </el-button>
          </div>

          <el-card class="repo-list-card">
            <el-table :data="repositories" border>
              <el-table-column prop="name" label="仓库名称" min-width="150" />
              <el-table-column prop="remote_url" label="远程地址" min-width="200" />
              <el-table-column prop="branch" label="分支" width="100" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="scope">
                  <el-tag :type="scope.row.status === 'cloned' ? 'success' : 'warning'">
                    {{ scope.row.status === 'cloned' ? '已克隆' : scope.row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="is_dirty" label="是否修改" width="100">
                <template #default="scope">
                  <el-tag v-if="scope.row.is_dirty" type="warning">已修改</el-tag>
                  <el-tag v-else type="success">干净</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="last_synced_at" label="最后同步" width="180" />
              <el-table-column label="操作" width="200">
                <template #default="scope">
                  <el-button size="small" @click="viewCommits(scope.row)">
                    <el-icon><Clock /></el-icon>
                    提交历史
                  </el-button>
                  <el-button size="small" @click="syncRepo(scope.row)">
                    <el-icon><Refresh /></el-icon>
                    同步
                  </el-button>
                  <el-button size="small" @click="configureWebhook(scope.row)">
                    <el-icon><Setting /></el-icon>
                    Webhook
                  </el-button>
                  <el-button size="small" type="danger" @click="deleteRepo(scope.row)">
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div v-if="repositories.length === 0" class="empty-state">
              <el-icon :size="64" style="color: #ccc;"><FolderOpened /></el-icon>
              <p>暂无仓库，点击上方按钮添加</p>
            </div>
          </el-card>
        </div>

        <el-dialog title="添加仓库" v-model="showCreateModal" width="600px">
          <el-form :model="repoForm" label-width="100px">
            <el-form-item label="仓库名称" prop="name">
              <el-input v-model="repoForm.name" placeholder="输入仓库名称" />
            </el-form-item>
            <el-form-item label="远程地址" prop="remote_url">
              <el-input v-model="repoForm.remote_url" placeholder="https://... 或 git@..." />
            </el-form-item>
            <el-form-item label="分支" prop="branch">
              <el-input v-model="repoForm.branch" placeholder="main" />
            </el-form-item>
            <el-form-item label="认证类型" prop="auth_type">
              <el-select v-model="repoForm.auth_type">
                <el-option label="无" value="none" />
                <el-option label="SSH" value="ssh" />
                <el-option label="Token" value="token" />
                <el-option label="密码" value="password" />
              </el-select>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showCreateModal = false">取消</el-button>
            <el-button type="primary" @click="createRepo" :loading="submitting" :disabled="submitting">确定</el-button>
          </template>
        </el-dialog>

        <el-dialog title="Webhook 配置" v-model="showWebhookModal" width="500px">
          <el-form :model="webhookForm" label-width="120px">
            <el-form-item label="服务提供商">
              <el-select v-model="webhookForm.provider">
                <el-option label="GitHub" value="github" />
                <el-option label="GitLab" value="gitlab" />
                <el-option label="Gitea" value="gitea" />
                <el-option label="Bitbucket" value="bitbucket" />
              </el-select>
            </el-form-item>
            <el-form-item label="签名密钥">
              <el-input v-model="webhookForm.webhook_secret" placeholder="可选，用于验证签名" />
            </el-form-item>
            <el-form-item label="启用 Webhook">
              <el-switch v-model="webhookForm.enabled" />
            </el-form-item>
            <el-form-item label="自动拉取">
              <el-switch v-model="webhookForm.auto_pull" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showWebhookModal = false">取消</el-button>
            <el-button type="primary" @click="saveWebhookConfig">保存</el-button>
          </template>
        </el-dialog>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Plus, Clock, Refresh, Setting, Delete, FolderOpened } from '@element-plus/icons-vue';
import LayoutHeader from '../components/Layout/Header.vue';
import LayoutSidebar from '../components/Layout/Sidebar.vue';
import { getRepositories, createRepository, syncRepository, deleteRepository, updateWebhookConfig, getWebhookConfig } from '../api/git';
const repositories = ref([]);
const showCreateModal = ref(false);
const showWebhookModal = ref(false);
const submitting = ref(false);
const repoForm = ref({
 name: '',
 remote_url: '',
 branch: 'main',
 auth_type: 'none'
});
const webhookForm = ref({
 provider: 'github',
 webhook_secret: '',
 enabled: true,
 auto_pull: true
});
const currentRepo = ref(null);
const loadRepositories = async () => {
 try {
 const response = await getRepositories();
 repositories.value = response.data.repositories || [];
 }
 catch (error) {
 console.error('加载仓库列表失败:', error);
 }
};
const createRepo = async () => {
 submitting.value = true;
 try {
 await createRepository(repoForm.value);
 showCreateModal.value = false;
 repoForm.value = { name: '', remote_url: '', branch: 'main', auth_type: 'none' };
 await loadRepositories();
 ElMessage.success('仓库创建成功');
 }
 catch (error) {
 console.error('创建仓库失败:', error.response?.data?.detail || error.message);
 }
 finally {
 submitting.value = false;
 }
};
const viewCommits = (repo) => {
 window.location.href = `/git/commits/${repo.id}`;
};
const syncRepo = async (repo) => {
 try {
 await syncRepository(repo.id);
 await loadRepositories();
 ElMessage.success('同步成功');
 }
 catch (error) {
 console.error('同步仓库失败:', error.response?.data?.detail || error.message);
 }
};
const configureWebhook = async (repo) => {
 currentRepo.value = repo;
 webhookForm.value = {
 provider: 'github',
 webhook_secret: '',
 enabled: true,
 auto_pull: true
 };
 try {
 const response = await getWebhookConfig(repo.id);
 webhookForm.value = {
 provider: response.data.provider || 'github',
 webhook_secret: '',
 enabled: response.data.enabled,
 auto_pull: response.data.auto_pull
 };
 }
 catch (error) {
 console.log('Webhook 配置不存在，使用默认值');
 }
 showWebhookModal.value = true;
};
const saveWebhookConfig = async () => {
 try {
 await updateWebhookConfig(currentRepo.value.id, webhookForm.value);
 showWebhookModal.value = false;
 ElMessage.success('Webhook 配置已保存');
 }
 catch (error) {
 console.error('保存 Webhook 配置失败:', error.response?.data?.detail || error.message);
 }
};
const deleteRepo = async (repo) => {
 if (confirm(`确定要删除仓库 "${repo.name}" 吗？`)) {
 try {
 await deleteRepository(repo.id);
 await loadRepositories();
 ElMessage.success('仓库已删除');
 }
 catch (error) {
 console.error('删除仓库失败:', error.response?.data?.detail || error.message);
 }
 }
};
onMounted(() => {
 loadRepositories();
});
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

.page-title {
  margin-bottom: 20px;
  font-size: 24px;
  color: #333;
}
</style>