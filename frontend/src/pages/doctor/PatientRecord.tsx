import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import {
  fetchPatientRecord, updateRegistrationStatus,
  updateCase, deleteCase, updateVisit, deleteVisit,
  updatePrescription, deletePrescription,
  createCarePlan, updateCarePlan, deleteCarePlan,
} from '../../api/doctor'
import PatientRecordView from '../../components/doctor/PatientRecordView'
import type { PatientRecordData } from '../../types'

const TOKEN = () => localStorage.getItem('token') || ''

const STATUS_LABELS: Record<string, string> = {
  registered: '已挂号',
  in_consultation: '问诊中',
  recovering: '康复中',
  recovered: '已康复',
  need_reregister: '未到请重新挂号',
}

const STATUS_COLORS: Record<string, string> = {
  registered: '#4f46e5',
  in_consultation: '#10b981',
  recovering: '#f59e0b',
  recovered: '#94a3b8',
  need_reregister: '#ef4444',
}

const TRANSITIONS: Record<string, { label: string; target: string; color: string }[]> = {
  registered: [
    { label: '开始问诊', target: 'in_consultation', color: '#10b981' },
    { label: '标记未到', target: 'need_reregister', color: '#ef4444' },
  ],
  in_consultation: [
    { label: '进入康复', target: 'recovering', color: '#f59e0b' },
  ],
  recovering: [
    { label: '确认康复', target: 'recovered', color: '#10b981' },
  ],
}

async function apiPost(url: string, body: unknown) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN()}` },
    body: JSON.stringify(body),
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`POST ${url} failed: ${resp.status}`)
  }
  return resp.json()
}

export default function PatientRecord() {
  const { patientId } = useParams<{ patientId: string }>()
  const [patient, setPatient] = useState<PatientRecordData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusMsg, setStatusMsg] = useState('')
  const navigate = useNavigate()
  const logout = useAuthStore((s) => s.logout)
  const token = useAuthStore((s) => s.token)

  const loadPatient = () => {
    if (!patientId) return
    setLoading(true)
    setError('')
    fetchPatientRecord(Number(patientId))
      .then(setPatient)
      .catch((err) => setError('加载失败: ' + (err.message || '未知错误')))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (!token) { navigate('/login'); return }
    loadPatient()
  }, [patientId, token])

  const regStatus = patient?.current_registration_status || ''
  const regDept = patient?.current_registration_department || ''
  const editable = regStatus === 'in_consultation' || regStatus === 'recovering'
  const transitions = TRANSITIONS[regStatus] || []

  // Find active episode for create operations
  const activeEpisode = patient?.episodes.find(
    (ep) => ['registered', 'in_consultation', 'recovering'].includes(ep.status)
  )
  const activeRegId = activeEpisode?.registration_id ?? null

  const handleStatusTransition = async (target: string) => {
    setStatusMsg('')
    try {
      await updateRegistrationStatus(Number(patientId), { status: target })
      setStatusMsg(`状态更新成功: ${STATUS_LABELS[target] || target}`)
      loadPatient()
    } catch (e: any) {
      setStatusMsg(`操作失败: ${e.message}`)
    }
  }

  const handleCreateCase = async (_regId: number, data: Record<string, string>) => {
    await apiPost(`/api/doctor/patient/${patientId}/cases`, data)
    loadPatient()
  }

  const handleCreateVisit = async (_regId: number, data: Record<string, string>) => {
    await apiPost(`/api/doctor/patient/${patientId}/visits`, data)
    loadPatient()
  }

  const handleCreatePrescription = async (_regId: number, data: Record<string, string>) => {
    await apiPost(`/api/doctor/patient/${patientId}/prescriptions`, data)
    loadPatient()
  }

  const handleCreateCarePlan = async (_regId: number, data: Record<string, string>) => {
    await createCarePlan(Number(patientId), { title: data.title, description: data.description, medication_schedule: data.medication_schedule, follow_up_date: data.follow_up_date })
    loadPatient()
  }

  const handleUpdateCase = async (id: number, data: Record<string, string>) => {
    await updateCase(id, data)
    loadPatient()
  }

  const handleDeleteCase = async (id: number) => {
    await deleteCase(id)
    loadPatient()
  }

  const handleUpdateVisit = async (id: number, data: Record<string, string>) => {
    await updateVisit(id, data)
    loadPatient()
  }

  const handleDeleteVisit = async (id: number) => {
    await deleteVisit(id)
    loadPatient()
  }

  const handleUpdatePrescription = async (id: number, data: Record<string, string>) => {
    await updatePrescription(id, data)
    loadPatient()
  }

  const handleDeletePrescription = async (id: number) => {
    await deletePrescription(id)
    loadPatient()
  }

  const handleUpdateCarePlan = async (id: number, data: Record<string, string>) => {
    await updateCarePlan(id, data)
    loadPatient()
  }

  const handleDeleteCarePlan = async (id: number) => {
    await deleteCarePlan(id)
    loadPatient()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f8fafc' }}>
      <header style={{
        background: 'linear-gradient(135deg, #4338ca, #6366f1)',
        padding: '14px 28px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 12px rgba(79,70,229,0.2)',
      }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, fontWeight: 700, color: '#fff' }}>R</div>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#fff' }}>患者记录</h2>
          <button onClick={() => navigate('/doctor/chat')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}>
            智能问诊
          </button>
          <button onClick={() => navigate('/doctor/patients')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13 }}>
            患者列表
          </button>
          <button onClick={() => navigate('/doctor/search-history')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13 }}>
            检索历史
          </button>
        </div>
        <button onClick={() => { logout(); navigate('/login') }} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 8, background: 'rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer', fontSize: 13, backdropFilter: 'blur(4px)' }}>
          退出
        </button>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 16px', maxWidth: 900, margin: '0 auto', width: '100%' }}>
        {loading && <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>加载中...</div>}
        {error && <div style={{ padding: '12px 16px', background: '#fef2f2', borderRadius: 10, border: '1px solid #fecaca', color: '#dc2626', fontSize: 14 }}>{error}</div>}

        {/* Registration status banner */}
        {regStatus && (
          <div style={{ background: '#fff', border: '1px solid #c7d2fe', borderRadius: 12, padding: '14px 18px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <span style={{ fontSize: 13, color: '#64748b' }}>
              挂号状态：{regDept ? <span style={{ color: '#1e293b', fontWeight: 500 }}>{regDept} · </span> : ''}
            </span>
            <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: 6, background: STATUS_COLORS[regStatus] || '#94a3b8', color: '#fff', fontSize: 12, fontWeight: 600 }}>
              {STATUS_LABELS[regStatus] || regStatus}
            </span>
            {transitions.length > 0 && (
              <div style={{ display: 'flex', gap: 8, marginLeft: 'auto' }}>
                {transitions.map((t) => (
                  <button
                    key={t.target}
                    onClick={() => handleStatusTransition(t.target)}
                    style={{ padding: '6px 14px', border: `1.5px solid ${t.color}`, borderRadius: 6, background: '#fff', color: t.color, cursor: 'pointer', fontSize: 12, fontWeight: 500 }}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {statusMsg && (
          <div style={{ padding: '10px 14px', background: statusMsg.includes('失败') ? '#fef2f2' : '#f0fdf4', border: `1px solid ${statusMsg.includes('失败') ? '#fecaca' : '#bbf7d0'}`, borderRadius: 10, color: statusMsg.includes('失败') ? '#dc2626' : '#16a34a', fontSize: 13, marginBottom: 16 }}>{statusMsg}</div>
        )}

        {patient && (
          <PatientRecordView
            patient={patient}
            editable={editable}
            activeRegistrationId={activeRegId}
            onCreateCase={handleCreateCase}
            onCreateVisit={handleCreateVisit}
            onCreatePrescription={handleCreatePrescription}
            onCreateCarePlan={handleCreateCarePlan}
            onUpdateCase={handleUpdateCase}
            onDeleteCase={handleDeleteCase}
            onUpdateVisit={handleUpdateVisit}
            onDeleteVisit={handleDeleteVisit}
            onUpdatePrescription={handleUpdatePrescription}
            onDeletePrescription={handleDeletePrescription}
            onUpdateCarePlan={handleUpdateCarePlan}
            onDeleteCarePlan={handleDeleteCarePlan}
          />
        )}
      </div>
    </div>
  )
}
