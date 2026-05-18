<template>
  <el-aside width="220px" class="sidebar">
    <div class="logo">
      <h2>审计系统</h2>
    </div>
    
    <el-menu
      :default-active="activeMenu"
      class="sidebar-menu"
      :collapse="isCollapse"
      @select="handleSelect"
    >
      <el-menu-item index="/">
        <el-icon><HomeFilled /></el-icon>
        <template #title>仪表盘</template>
      </el-menu-item>
      
      <el-menu-item index="/files">
        <el-icon><Folder /></el-icon>
        <template #title>文件浏览</template>
      </el-menu-item>
      
      <el-menu-item index="/audit">
        <el-icon><List /></el-icon>
        <template #title>审计日志</template>
      </el-menu-item>
      
      <el-sub-menu v-if="isAdmin" index="system">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>系统管理</span>
        </template>
        
        <el-menu-item index="/users">
          <el-icon><User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
        
        <el-menu-item index="/settings">
          <el-icon><Tools /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
      </el-sub-menu>
    </el-menu>
  </el-aside>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { HomeFilled, Folder, List, Setting, User, Tools } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isCollapse = ref(false)

const activeMenu = computed(() => {
  const path = route.path
  if (path === '/') return '/'
  return '/' + path.split('/')[1]
})

const isAdmin = computed(() => {
  return authStore.user?.role === 'admin'
})

const handleSelect = (index) => {
  router.push(index)
}
</script>

<style scoped>
.sidebar {
  background: #304156;
  height: 100%;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #263445;
}

.logo h2 {
  margin: 0;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
}

.sidebar-menu {
  border-right: none;
  background: #304156;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 220px;
}

.sidebar-menu .el-menu-item,
.sidebar-menu .el-sub-menu__title {
  color: #bfcbd9;
}

.sidebar-menu .el-menu-item:hover,
.sidebar-menu .el-sub-menu__title:hover {
  background: #263445;
  color: #409eff;
}

.sidebar-menu .el-menu-item.is-active {
  background: #263445;
  color: #409eff;
}

.sidebar-menu .el-sub-menu .el-menu-item {
  padding-left: 50px !important;
}

.sidebar-menu .el-sub-menu .el-menu-item.is-active {
  background: #263445;
  color: #409eff;
}
</style>
