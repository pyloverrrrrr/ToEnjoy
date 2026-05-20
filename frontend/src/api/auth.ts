import type { UserMeData } from '../types'

export function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('token')
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

const TOKEN = () => localStorage.getItem('token') || ''

export async function fetchMe(): Promise<UserMeData> {
  const resp = await fetch('/api/auth/me', {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Fetch me failed: ${resp.status}`)
  }
  return resp.json()
}

export async function updateMe(data: Partial<Pick<UserMeData, 'name' | 'phone' | 'email'>>): Promise<UserMeData> {
  const resp = await fetch('/api/auth/me', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN()}`,
    },
    body: JSON.stringify(data),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Update me failed: ${resp.status}`)
  }
  return resp.json()
}

export async function uploadAvatar(file: File): Promise<string> {
  const formData = new FormData()
  formData.append('file', file)
  const resp = await fetch('/api/auth/avatar', {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOKEN()}` },
    body: formData,
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Upload avatar failed: ${resp.status}`)
  }
  const data = await resp.json()
  return data.avatar_url
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  const resp = await fetch('/api/auth/password', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN()}`,
    },
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    const data = await resp.json().catch(() => ({}))
    throw new Error(data.detail || `Change password failed: ${resp.status}`)
  }
}

export async function deleteAccount(password: string, confirmPassword: string): Promise<void> {
  const resp = await fetch('/api/auth/delete-account', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN()}`,
    },
    body: JSON.stringify({ password, confirm_password: confirmPassword }),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    const data = await resp.json().catch(() => ({}))
    throw new Error(data.detail || `Delete account failed: ${resp.status}`)
  }
}
