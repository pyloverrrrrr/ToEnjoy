import type { PatientProfileData, CarePlanEpisodeData, MedicalRecordsEpisodeData } from '../types'

const TOKEN = () => localStorage.getItem('token') || ''

export async function fetchProfile(): Promise<PatientProfileData> {
  const resp = await fetch('/api/patient/profile', {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Fetch profile failed: ${resp.status}`)
  }
  return resp.json()
}

export async function updateProfile(
  data: Partial<Omit<PatientProfileData, 'user_id'>>
): Promise<PatientProfileData> {
  const resp = await fetch('/api/patient/profile', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN()}`,
    },
    body: JSON.stringify(data),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Update profile failed: ${resp.status}`)
  }
  return resp.json()
}

export async function fetchCarePlan(): Promise<CarePlanEpisodeData> {
  const resp = await fetch('/api/patient/care-plan', {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Fetch care plan failed: ${resp.status}`)
  }
  return resp.json()
}

export async function fetchMedicalRecords(): Promise<MedicalRecordsEpisodeData> {
  const resp = await fetch('/api/patient/medical-records', {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Fetch medical records failed: ${resp.status}`)
  }
  return resp.json()
}
