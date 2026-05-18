import api from './index'

export const fetchDirectoryTree = (path = '/') => {
  return api.get('/files/list', { params: { path } })
}

export const fetchFiles = (params) => {
  return api.get('/files/list', { params })
}

export const fetchFileContent = (filePath) => {
  return api.get('/files/read', { params: { path: filePath } })
}

export const createDirectory = (path, name) => {
  return api.post('/files/directory', null, { params: { path, name } })
}

export const uploadFile = (formData) => {
  return api.post('/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const deleteFile = (path) => {
  return api.delete('/files/delete', { params: { path } })
}

export const renameFile = (oldPath, newPath) => {
  return api.put('/files/rename', null, { params: { old_path: oldPath, new_path: newPath } })
}

export const moveFile = (sourcePath, targetPath) => {
  return api.put('/files/move', null, { params: { source_path: sourcePath, target_path: targetPath } })
}

export const copyFile = (sourcePath, targetPath) => {
  return api.post('/files/copy', null, { params: { source_path: sourcePath, target_path: targetPath } })
}

export const downloadFile = (path) => {
  return api.get('/files/download', { params: { path }, responseType: 'blob' })
}
