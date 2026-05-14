import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, refreshToken as apiRefreshToken, fetchUserInfo } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token') || '')
  const refreshTokenValue = ref(localStorage.getItem('refreshToken') || '')

  const isAuthenticated = computed(() => !!token.value)

  async function login(username, password) {
    try {
      console.log('开始登录，用户名:', username)
      const response = await apiLogin(username, password)
      console.log('登录响应:', response)
      
      token.value = response.data.access_token
      refreshTokenValue.value = response.data.refresh_token || ''
      user.value = response.data.user
      
      console.log('设置 token:', token.value)
      console.log('设置 user:', user.value)
      
      localStorage.setItem('token', token.value)
      if (refreshTokenValue.value) {
        localStorage.setItem('refreshToken', refreshTokenValue.value)
      }
      
      console.log('localStorage 中的 token:', localStorage.getItem('token'))
      
      return { success: true }
    } catch (error) {
      console.error('登录错误:', error)
      return { success: false, message: error.response?.data?.detail || '登录失败' }
    }
  }

  function logout() {
    user.value = null
    token.value = ''
    refreshTokenValue.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
  }

  async function refreshToken() {
    try {
      const response = await apiRefreshToken(refreshTokenValue.value)
      token.value = response.data.access_token
      localStorage.setItem('token', token.value)
      return true
    } catch (error) {
      logout()
      return false
    }
  }

  async function fetchUser() {
    try {
      const response = await fetchUserInfo()
      user.value = response.data
    } catch (error) {
      console.error('获取用户信息失败:', error)
    }
  }

  return {
    user,
    token,
    isAuthenticated,
    login,
    logout,
    refreshToken,
    fetchUser
  }
})
