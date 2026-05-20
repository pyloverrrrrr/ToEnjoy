import type { PatientRecordData, DoctorProfileData, CarePlanItemData, CarePlanCreateData, RegisteredPatientItem, RegistrationInfo } from '../types'

const TOKEN = () => localStorage.getItem('token') || ''

export interface PatientSearchItem {
  id: number
  name: string
  phone?: string
  id_number_suffix?: string
}

export async function searchPatients(query: string): Promise<PatientSearchItem[]> {
  const resp = await fetch(`/api/doctor/patients?q=${encodeURIComponent(query)}`, {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Search patients failed: ${resp.status}`)
  }
  return resp.json()
}

export async function fetchPatientRecord(patientId: number): Promise<PatientRecordData> {
  const resp = await fetch(`/api/doctor/patient/${patientId}`, {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Fetch patient record failed: ${resp.status}`)
  }
  return resp.json()
}

export async function fetchDoctorProfile(): Promise<DoctorProfileData> {
  const resp = await fetch('/api/doctor/profile', {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Fetch doctor profile failed: ${resp.status}`)
  }
  return resp.json()
}

export async function fetchPatientCarePlans(patientId: number): Promise<{ plans: CarePlanItemData[]; total: number }> {
  const resp = await fetch(`/api/doctor/patient/${patientId}/care-plans`, {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Fetch care plans failed: ${resp.status}`)
  }
  return resp.json()
}

export async function createCarePlan(patientId: number, data: CarePlanCreateData): Promise<CarePlanItemData> {
  const resp = await fetch(`/api/doctor/patient/${patientId}/care-plan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN()}`,
    },
    body: JSON.stringify(data),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Create care plan failed: ${resp.status}`)
  }
  return resp.json()
}

export async function updateCarePlan(planId: number, data: Partial<CarePlanCreateData & { status: string }>): Promise<CarePlanItemData> {
  const resp = await fetch(`/api/doctor/care-plan/${planId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN()}`,
    },
    body: JSON.stringify(data),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Update care plan failed: ${resp.status}`)
  }
  return resp.json()
}

export async function deleteCarePlan(planId: number): Promise<void> {
  const resp = await fetch(`/api/doctor/care-plan/${planId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Delete care plan failed: ${resp.status}`)
  }
}

export async function updateDoctorProfile(
  data: Partial<Omit<DoctorProfileData, 'user_id'>>
): Promise<DoctorProfileData> {
  const resp = await fetch('/api/doctor/profile', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN()}`,
    },
    body: JSON.stringify(data),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Update doctor profile failed: ${resp.status}`)
  }
  return resp.json()
}

export async function fetchRegisteredPatients(q?: string): Promise<RegisteredPatientItem[]> {
  const params = q ? `?q=${encodeURIComponent(q)}` : ''
  const resp = await fetch(`/api/doctor/patients${params}`, {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Fetch registered patients failed: ${resp.status}`)
  }
  return resp.json()
}

export async function updateCase(caseId: number, data: Record<string, string | undefined>): Promise<Record<string, unknown>> {
  const resp = await fetch(`/api/doctor/case/${caseId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN()}` },
    body: JSON.stringify(data),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Update case failed: ${resp.status}`)
  }
  return resp.json()
}

export async function deleteCase(caseId: number): Promise<void> {
  const resp = await fetch(`/api/doctor/case/${caseId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Delete case failed: ${resp.status}`)
  }
}

export async function updateVisit(visitId: number, data: Record<string, string | undefined>): Promise<Record<string, unknown>> {
  const resp = await fetch(`/api/doctor/visit/${visitId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN()}` },
    body: JSON.stringify(data),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Update visit failed: ${resp.status}`)
  }
  return resp.json()
}

export async function deleteVisit(visitId: number): Promise<void> {
  const resp = await fetch(`/api/doctor/visit/${visitId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Delete visit failed: ${resp.status}`)
  }
}

export async function updatePrescription(prescriptionId: number, data: Record<string, string | undefined>): Promise<Record<string, unknown>> {
  const resp = await fetch(`/api/doctor/prescription/${prescriptionId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN()}` },
    body: JSON.stringify(data),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Update prescription failed: ${resp.status}`)
  }
  return resp.json()
}

export async function deletePrescription(prescriptionId: number): Promise<void> {
  const resp = await fetch(`/api/doctor/prescription/${prescriptionId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Delete prescription failed: ${resp.status}`)
  }
}

export async function updateRegistrationStatus(
  patientId: number,
  data: { status: string; notes?: string }
): Promise<RegistrationInfo> {
  const resp = await fetch(`/api/doctor/patient/${patientId}/registration-status`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN()}`,
    },
    body: JSON.stringify(data),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    const errData = await resp.json().catch(() => ({}))
    throw new Error(errData.detail || `Update registration status failed: ${resp.status}`)
  }
  return resp.json()
}

export async function dismissDeletedPatient(patientId: number): Promise<void> {
  const resp = await fetch(`/api/doctor/patient/${patientId}/dismiss`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Dismiss patient failed: ${resp.status}`)
  }
}
