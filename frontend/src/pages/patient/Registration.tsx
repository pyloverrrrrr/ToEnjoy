import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchDepartments, fetchMyRegistration, submitRegistration } from '../../api/registration'
import type { DepartmentInfo, RegistrationInfo } from '../../types'

const STATUS_LABELS: Record<string, string> = {
  registered: '已挂号',
  in_consultation: '问诊中',
  recovering: '康复中',
  recovered: '已康复',
  need_reregister: '未到请重新挂号',
}

const STATUS_COLORS: Record<string, string> = {
  registered: '#e11d48',
  in_consultation: '#10b981',
  recovering: '#f59e0b',
  recovered: '#94a3b8',
  need_reregister: '#ef4444',
}

export default function PatientRegistration() {
  const navigate = useNavigate()
  const [registration, setRegistration] = useState<RegistrationInfo | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [departments, setDepartments] = useState<DepartmentInfo[]>([])
  const [selectedDept, setSelectedDept] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadData = useCallback(async () => {
    try {
      const [regData, deptData] = await Promise.all([fetchMyRegistration(), fetchDepartments()])
      if ('registered' in regData && !regData.registered) {
        setRegistration(null)
      } else {
        setRegistration(regData as RegistrationInfo)
      }
      setDepartments(deptData)
    } catch (e) {
      setError('加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const handleSubmit = async () => {
    if (!selectedDept) { setError('请选择科室'); return }
    setIsSubmitting(true)
    setError('')
    try {
      const result = await submitRegistration(selectedDept)
      setRegistration(result)
      setSuccess('挂号成功！请等待医生接诊')
    } catch (e: any) {
      setError(e.message || '挂号失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  const statusLabel = (s: string) => STATUS_LABELS[s] || s
  const statusColor = (s: string) => STATUS_COLORS[s] || '#94a3b8'
  const needsRegistration = !registration || registration.status === 'need_reregister' || registration.status === 'recovered'

  if (isLoading) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fef2f2' }}>
        <div style={{ textAlign: 'center', color: '#94a3b8', padding: 48 }}>加载中...</div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: '#fef2f2', padding: '28px 16px' }}>
      <div style={{ maxWidth: 600, margin: '0 auto' }}>
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, alignItems: 'center' }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#e11d48', margin: 0 }}>挂号就诊</h2>
          <div style={{ flex: 1 }} />
          <button onClick={() => navigate('/patient/chat')} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#e11d48', fontWeight: 500 }}>返回对话</button>
          <button onClick={() => navigate('/patient/history')} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#64748b' }}>对话历史</button>
          <button onClick={() => navigate('/patient/profile')} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#64748b' }}>个人档案</button>
        </div>

        {error && (
          <div style={{ padding: '10px 14px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, color: '#dc2626', fontSize: 13, marginBottom: 16 }}>{error}</div>
        )}
        {success && (
          <div style={{ padding: '10px 14px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 10, color: '#16a34a', fontSize: 13, marginBottom: 16 }}>{success}</div>
        )}

        {/* Current Registration Status (read-only) */}
        {registration && (
          <div style={{ background: '#fff', border: '1px solid #fecdd3', borderRadius: 12, padding: 24, marginBottom: 24, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 12px 0', color: '#1e293b' }}>当前挂号信息</h3>
            <div style={{ fontSize: 14, lineHeight: 2, color: '#334155' }}>
              <div><span style={{ color: '#94a3b8' }}>序号：</span>第 {registration.sequence_number || 1} 次挂号</div>
              <div><span style={{ color: '#94a3b8' }}>科室：</span>{registration.department}</div>
              <div>
                <span style={{ color: '#94a3b8' }}>状态：</span>
                <span style={{
                  display: 'inline-block',
                  padding: '2px 10px',
                  borderRadius: 6,
                  background: statusColor(registration.status),
                  color: '#fff',
                  fontSize: 12,
                  fontWeight: 600,
                }}>{statusLabel(registration.status)}</span>
              </div>
              {registration.status_notes && (
                <div><span style={{ color: '#94a3b8' }}>备注：</span>{registration.status_notes}</div>
              )}
              <div><span style={{ color: '#94a3b8' }}>挂号日期：</span>{registration.registration_date?.slice(0, 10)}</div>
            </div>
          </div>
        )}

        {/* Registration Form (when no active registration) */}
        {needsRegistration && (
          <div style={{ background: '#fff', border: '1px solid #fecdd3', borderRadius: 12, padding: 24, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px 0', color: '#1e293b' }}>
              {registration?.status === 'need_reregister' ? '重新挂号（上次挂号已作废）' : registration?.status === 'recovered' ? '重新挂号（上次诊疗已结束）' : '选择科室挂号'}
            </h3>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 13, color: '#64748b', fontWeight: 500, marginBottom: 6 }}>选择科室</label>
              <select
                value={selectedDept}
                onChange={(e) => { setSelectedDept(e.target.value); setError('') }}
                style={{ width: '100%', padding: '10px 14px', border: '1.5px solid #e2e8f0', borderRadius: 10, fontSize: 14, background: '#f8fafc', color: '#1e293b' }}
              >
                <option value="">请选择科室</option>
                {departments.map((d) => (
                  <option key={d.name} value={d.name}>
                    {d.name}{d.doctor_count > 0 ? `（${d.doctor_count}位医生）` : '（暂无医生）'}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleSubmit}
              disabled={isSubmitting || !selectedDept}
              style={{
                width: '100%',
                padding: '12px 0',
                background: isSubmitting || !selectedDept ? '#fda4af' : 'linear-gradient(135deg, #be123c, #e11d48)',
                color: '#fff',
                border: 'none',
                borderRadius: 10,
                fontSize: 15,
                fontWeight: 600,
                cursor: isSubmitting || !selectedDept ? 'not-allowed' : 'pointer',
                boxShadow: isSubmitting || !selectedDept ? 'none' : '0 2px 8px rgba(225,29,72,0.25)',
              }}
            >
              {isSubmitting ? '提交中...' : '确认挂号'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
