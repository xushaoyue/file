import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    console.log('请求拦截器 - token:', token)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      console.log('添加 Authorization header:', config.headers.Authorization)
    }
    console.log('请求配置:', config)
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  response => {
    return response
  },
  async error => {
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          const authStore = useAuthStore()
          if (authStore.refreshTokenValue) {
            try {
              await authStore.refreshToken()
              error.config.headers.Authorization = `Bearer ${authStore.token}`
              return api.request(error.config)
            } catch {
              ElMessage.warning('登录已过期，请重新登录')
              authStore.logout()
              router.push('/login')
            }
          } else {
            ElMessage.warning('登录已过期，请重新登录')
            authStore.logout()
            router.push('/login')
          }
          break
        case 403:
          ElMessage.error('权限不足')
          break
        case 404:
          ElMessage.error('资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误')
          break
        default:
          ElMessage.error(data.detail || data.message || '请求失败')
      }
    } else if (error.request) {
      ElMessage.error('网络连接失败')
    } else {
      ElMessage.error('请求配置错误')
    }
    
    return Promise.reject(error)
  }
)

export default api
