import type { DepartmentInfo, RegistrationInfo } from '../types'

const TOKEN = () => localStorage.getItem('token') || ''

export async function fetchDepartments(): Promise<DepartmentInfo[]> {
  const resp = await fetch('/api/departments', {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Fetch departments failed: ${resp.status}`)
  }
  return resp.json()
}

export async function fetchMyRegistration(): Promise<RegistrationInfo | { registered: false }> {
  const resp = await fetch('/api/patient/registration', {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Fetch registration failed: ${resp.status}`)
  }
  return resp.json()
}

export async function submitRegistration(department: string): Promise<RegistrationInfo> {
  const resp = await fetch('/api/patient/registration', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN()}`,
    },
    body: JSON.stringify({ department }),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    if (resp.status === 409) {
      const data = await resp.json()
      throw new Error(data.detail || '您已有进行中的挂号')
    }
    throw new Error(`Submit registration failed: ${resp.status}`)
  }
  return resp.json()
}
