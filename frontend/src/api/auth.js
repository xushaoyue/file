import api from './index'

export const login = (username, password) => {
  const formData = new FormData()
  formData.append('username', username)
  formData.append('password', password)
  return api.post('/auth/login', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
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
