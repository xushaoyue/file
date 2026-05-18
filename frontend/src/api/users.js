import api from './index'

export const fetchUsers = (params) => {
  return api.get('/users', { params })
}

export const fetchUserById = (id) => {
  return api.get(`/users/${id}`)
}

export const createUser = (data) => {
  return api.post('/users', data)
}

export const updateUser = (id, data) => {
  return api.put(`/users/${id}`, data)
}

export const deleteUser = (id) => {
  return api.delete(`/users/${id}`)
}

export const resetPassword = (id) => {
  return api.post(`/users/${id}/reset-password`)
}

export const updatePermissions = (id, permissions) => {
  return api.put(`/users/${id}/permissions`, { permissions })
}

export const fetchRoles = () => {
  return api.get('/users/roles')
}

export const changePassword = (data) => {
  return api.post('/users/change-password', data)
}
