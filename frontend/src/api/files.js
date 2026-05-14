import api from './index'

export const fetchDirectoryTree = (path = '/') => {
  return api.get('/files/tree', { params: { path } })
}

export const fetchFiles = (params) => {
  return api.get('/files/', { params })
}

export const fetchFileContent = (filePath) => {
  return api.get('/files/content', { params: { path: filePath } })
}

export const createDirectory = (path, name) => {
  return api.post('/files/directory', { path, name })
}

export const uploadFile = (formData) => {
  return api.post('/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const deleteFile = (path) => {
  return api.delete('/files/', { params: { path } })
}

export const renameFile = (oldPath, newPath) => {
  return api.put('/files/rename', { old_path: oldPath, new_path: newPath })
}

export const moveFile = (sourcePath, targetPath) => {
  return api.put('/files/move', { source_path: sourcePath, target_path: targetPath })
}

export const copyFile = (sourcePath, targetPath) => {
  return api.post('/files/copy', { source_path: sourcePath, target_path: targetPath })
}

export const downloadFile = (path) => {
  return api.get('/files/download', { params: { path }, responseType: 'blob' })
}
