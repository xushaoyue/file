import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, refreshToken as apiRefreshToken, fetchUserInfo } from '@/api/auth'

function loadUser() {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref(loadUser())
  const token = ref(localStorage.getItem('token') || '')
  const refreshTokenValue = ref(localStorage.getItem('refreshToken') || '')

  const isAuthenticated = computed(() => !!token.value)

  async function login(username, password) {
    try {
      const response = await apiLogin(username, password)
      
      token.value = response.data.access_token
      refreshTokenValue.value = response.data.refresh_token || ''
      user.value = response.data.user
      
      localStorage.setItem('token', token.value)
      localStorage.setItem('user', JSON.stringify(response.data.user))
      if (refreshTokenValue.value) {
        localStorage.setItem('refreshToken', refreshTokenValue.value)
      }
      
      return { success: true }
    } catch (error) {
      return { success: false, message: error.response?.data?.detail || '登录失败' }
    }
  }

  function logout() {
    user.value = null
    token.value = ''
    refreshTokenValue.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('user')
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
      localStorage.setItem('user', JSON.stringify(response.data))
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
