import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/files',
    name: 'FileBrowser',
    component: () => import('@/views/FileBrowser.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/audit',
    name: 'AuditLogs',
    component: () => import('@/views/AuditLogs.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/users',
    name: 'UserManagement',
    component: () => import('@/views/UserManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/git/repositories',
    name: 'GitRepositories',
    component: () => import('@/views/GitRepositories.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/git/commits/:repoId',
    name: 'GitCommits',
    component: () => import('@/views/GitCommits.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const token = localStorage.getItem('token')
  
  const isAuthenticated = authStore.isAuthenticated || !!token
  
  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && isAuthenticated) {
    next('/')
  } else if (to.meta.requiresAdmin && authStore.user?.role !== 'admin') {
    next('/')
  } else {
    next()
  }
})

export default router
