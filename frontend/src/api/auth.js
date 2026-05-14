import api from './index'

export const login = (username, password) => {
  return api.post('/auth/login', { username, password })
}

export const refreshToken = (refreshToken) => {
  return api.post('/auth/refresh', { refresh_token: refreshToken })
}

export const fetchUserInfo = () => {
  return api.get('/auth/me')
}

export const logout = () => {
  return api.post('/auth/logout')
}
