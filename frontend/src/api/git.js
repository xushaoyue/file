import api from './index'

export const createRepository = (data) => {
  return api.post('/git/repositories', data)
}

export const getRepositories = () => {
  return api.get('/git/repositories')
}

export const getRepository = (repoId) => {
  return api.get(`/git/repositories/${repoId}`)
}

export const updateRepository = (repoId, data) => {
  return api.put(`/git/repositories/${repoId}`, data)
}

export const deleteRepository = (repoId) => {
  return api.delete(`/git/repositories/${repoId}`)
}

export const syncRepository = (repoId) => {
  return api.post(`/git/repositories/${repoId}/sync`)
}

export const getCommitHistory = (repoId, params) => {
  return api.get(`/git/repositories/${repoId}/commits`, { params })
}

export const getCommitDetail = (repoId, commitHash) => {
  return api.get(`/git/repositories/${repoId}/commits/${commitHash}`)
}

export const getDiff = (repoId, params) => {
  return api.get(`/git/repositories/${repoId}/diff`, { params })
}

export const getBlame = (repoId, params) => {
  return api.get(`/git/repositories/${repoId}/blame`, { params })
}

export const getBranches = (repoId) => {
  return api.get(`/git/repositories/${repoId}/branches`)
}

export const getTags = (repoId) => {
  return api.get(`/git/repositories/${repoId}/tags`)
}

export const getFileAtCommit = (repoId, commitHash, filePath) => {
  return api.get(`/git/repositories/${repoId}/files/${encodeURIComponent(filePath)}/at/${commitHash}`)
}

export const getWebhookConfig = (repoId) => {
  return api.get(`/git/repositories/${repoId}/webhook/config`)
}

export const updateWebhookConfig = (repoId, data) => {
  return api.put(`/git/repositories/${repoId}/webhook/config`, data)
}