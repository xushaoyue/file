<template>
  <el-container class="layout-container" direction="vertical">
    <LayoutHeader />
    <el-container class="layout-body">
      <LayoutSidebar />
      <el-main class="main-content">
        <div class="page-container">
          <div class="page-header">
            <h1 class="page-title">提交历史</h1>
            <el-button @click="goBack">
              <el-icon><ArrowLeft /></el-icon>
              返回仓库列表
            </el-button>
          </div>

          <el-card class="commit-list-card">
            <div class="commit-filters">
              <el-select v-model="branch" placeholder="选择分支">
                <el-option v-for="b in branches" :key="b.name" :label="b.name" :value="b.name" />
              </el-select>
              <el-pagination
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange"
                :current-page="page"
                :page-sizes="[10, 20, 50]"
                :page-size="pageSize"
                :total="total"
                layout="total, sizes, prev, pager, next, jumper"
              />
            </div>

            <div v-if="selectedCommit" class="commit-detail-panel">
              <div class="commit-detail-header">
                <el-button @click="selectedCommit = null" class="close-btn">
                  <el-icon><Close /></el-icon>
                </el-button>
                <h3>{{ selectedCommit.short_hash }} - {{ selectedCommit.message }}</h3>
              </div>
              <div class="commit-detail-info">
                <div class="info-row">
                  <span class="label">作者:</span>
                  <span>{{ selectedCommit.author_name }} &lt;{{ selectedCommit.author_email }}&gt;</span>
                </div>
                <div class="info-row">
                  <span class="label">提交者:</span>
                  <span>{{ selectedCommit.committer_name }} &lt;{{ selectedCommit.committer_email }}&gt;</span>
                </div>
                <div class="info-row">
                  <span class="label">时间:</span>
                  <span>{{ selectedCommit.committed_at }}</span>
                </div>
                <div class="info-row">
                  <span class="label">变更:</span>
                  <span>{{ selectedCommit.files_changed }} 个文件, +{{ selectedCommit.insertions }} -{{ selectedCommit.deletions }}</span>
                </div>
              </div>
              <div v-if="selectedCommit.diffs && selectedCommit.diffs.length" class="commit-diffs">
                <h4>变更详情</h4>
                <div v-for="diff in selectedCommit.diffs" :key="diff.filename" class="diff-item">
                  <div class="diff-header">
                    <span class="diff-filename">{{ diff.filename }}</span>
                    <el-tag :type="getDiffType(diff.change_type)">{{ getDiffLabel(diff.change_type) }}</el-tag>
                  </div>
                  <pre class="diff-content" v-if="diff.content">{{ diff.content }}</pre>
                </div>
              </div>
            </div>

            <div v-else class="commit-list">
              <div v-for="commit in commits" :key="commit.commit_hash" class="commit-item" @click="selectCommit(commit)">
                <div class="commit-sha">{{ commit.short_hash }}</div>
                <div class="commit-info">
                  <div class="commit-message">{{ commit.message }}</div>
                  <div class="commit-meta">
                    <span>{{ commit.author_name }}</span>
                    <span class="dot">·</span>
                    <span>{{ formatDate(commit.committed_at) }}</span>
                    <span class="dot">·</span>
                    <span>+{{ commit.insertions }} -{{ commit.deletions }}</span>
                  </div>
                </div>
                <div class="commit-actions">
                  <el-button size="small" @click.stop="viewBlame(commit)">
                    <el-icon><View /></el-icon>
                  </el-button>
                </div>
              </div>

              <div v-if="commits.length === 0" class="empty-state">
                <el-icon :size="64" style="color: #ccc;"><List /></el-icon>
                <p>暂无提交记录</p>
              </div>
            </div>
          </el-card>
        </div>

        <el-dialog title="Blame 信息" v-model="showBlameModal" width="800px">
          <div v-if="blameData" class="blame-container">
            <div class="blame-header">
              <span>{{ blameFile }}</span>
            </div>
            <div class="blame-content">
              <div v-for="line in blameData" :key="line.line_number" class="blame-line">
                <span class="line-number">{{ line.line_number }}</span>
                <span class="commit-hash">{{ line.short_hash }}</span>
                <span class="author-name">{{ line.author_name }}</span>
                <span class="line-content">{{ line.line_content }}</span>
              </div>
            </div>
          </div>
        </el-dialog>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>import { ref, onMounted, watch } from 'vue';
import { ArrowLeft, Close, View, List } from '@element-plus/icons-vue';
import LayoutHeader from '../components/Layout/Header.vue';
import LayoutSidebar from '../components/Layout/Sidebar.vue';
import { getCommitHistory, getCommitDetail, getBranches, getBlame } from '../api/git';
const commits = ref([]);
const branches = ref([]);
const selectedCommit = ref(null);
const blameData = ref(null);
const blameFile = ref('');
const showBlameModal = ref(false);
const repoId = ref(0);
const branch = ref('main');
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const loadCommits = async () => {
 try {
 const response = await getCommitHistory(repoId.value, {
 branch: branch.value,
 page: page.value,
 page_size: pageSize.value
 });
 commits.value = response.data.commits || [];
 total.value = response.data.total || 0;
 }
 catch (error) {
 console.error('加载提交历史失败:', error);
 }
};
const loadBranches = async () => {
 try {
 const response = await getBranches(repoId.value);
 branches.value = response.data.local_branches || [];
 if (branches.value.length > 0 && !branch.value) {
 branch.value = branches.value[0].name;
 }
 }
 catch (error) {
 console.error('加载分支列表失败:', error);
 }
};
const selectCommit = async (commit) => {
 try {
 const response = await getCommitDetail(repoId.value, commit.commit_hash);
 selectedCommit.value = response.data;
 }
 catch (error) {
 console.error('获取提交详情失败:', error);
 }
};
const viewBlame = async (commit) => {
 const filePath = prompt('请输入要查看 blame 的文件路径:');
 if (filePath) {
 try {
 const response = await getBlame(repoId.value, { file_path: filePath });
 blameData.value = response.data.blame;
 blameFile.value = filePath;
 showBlameModal.value = true;
 }
 catch (error) {
 console.error('获取 blame 信息失败:', error);
 }
 }
};
const goBack = () => {
 window.location.href = '/git/repositories';
};
const handleSizeChange = (val) => {
 pageSize.value = val;
 loadCommits();
};
const handleCurrentChange = (val) => {
 page.value = val;
 loadCommits();
};
const formatDate = (dateStr) => {
 if (!dateStr)
 return '';
 const date = new Date(dateStr);
 return date.toLocaleString();
};
const getDiffType = (type) => {
 const types = { A: 'success', D: 'danger', M: 'warning', R: 'info' };
 return types[type] || 'info';
};
const getDiffLabel = (type) => {
 const labels = { A: '新增', D: '删除', M: '修改', R: '重命名' };
 return labels[type] || type;
};
onMounted(() => {
 const path = window.location.pathname;
 const match = path.match(/\/git\/commits\/(\d+)/);
 if (match) {
 repoId.value = parseInt(match[1]);
 loadBranches();
 loadCommits();
 }
});
watch(branch, () => {
 page.value = 1;
 loadCommits();
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