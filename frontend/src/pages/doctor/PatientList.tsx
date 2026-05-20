import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchRegisteredPatients, updateRegistrationStatus, dismissDeletedPatient } from '../../api/doctor'
import type { RegisteredPatientItem } from '../../types'

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

const FILTER_TABS = [
  { key: '', label: '全部' },
  { key: 'registered', label: '已挂号' },
  { key: 'in_consultation', label: '问诊中' },
  { key: 'recovering', label: '康复中' },
  { key: 'recovered', label: '已康复' },
]

export default function DoctorPatientList() {
  const navigate = useNavigate()
  const [patients, setPatients] = useState<RegisteredPatientItem[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const loadPatients = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchRegisteredPatients(searchQuery || undefined)
      setPatients(data)
    } catch {
      // error handled by 401 redirect in API
    } finally {
      setLoading(false)
    }
  }, [searchQuery])

  useEffect(() => { loadPatients() }, [loadPatients])

  const filtered = statusFilter
    ? patients.filter((p) => p.registration_status === statusFilter)
    : patients

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') loadPatients()
  }

  const handleStatusTransition = async (patientId: number, target: string) => {
    try {
      await updateRegistrationStatus(patientId, { status: target })
      loadPatients()
    } catch {
      // silently fail, list just doesn't refresh
    }
  }

  const handleDismissDeleted = async (patientId: number) => {
    try {
      await dismissDeletedPatient(patientId)
      loadPatients()
    } catch {
      // silently fail
    }
  }

  const maskPhone = (phone?: string) => {
    if (!phone) return ''
    if (phone.length <= 4) return '****'
    return phone.slice(0, 3) + '****' + phone.slice(-4)
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', padding: '28px 16px' }}>
      <div style={{ maxWidth: 1000, margin: '0 auto' }}>
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, alignItems: 'center' }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#4f46e5', margin: 0 }}>患者列表</h2>
          <div style={{ flex: 1 }} />
          <button onClick={() => navigate('/doctor/chat')} style={{ padding: '6px 14px', border: '1px solid #c7d2fe', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#4f46e5', fontWeight: 500 }}>返回对话</button>
          <button onClick={() => navigate('/doctor/search')} style={{ padding: '6px 14px', border: '1px solid #c7d2fe', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#64748b' }}>知识检索</button>
          <button onClick={() => navigate('/doctor/profile')} style={{ padding: '6px 14px', border: '1px solid #c7d2fe', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#64748b' }}>个人档案</button>
        </div>

        {/* Search bar */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            placeholder="搜索患者姓名或手机号..."
            style={{ flex: 1, padding: '10px 14px', border: '1.5px solid #e2e8f0', borderRadius: 10, fontSize: 14, background: '#f8fafc', outline: 'none' }}
          />
          <button
            onClick={loadPatients}
            style={{ padding: '10px 24px', background: 'linear-gradient(135deg, #4338ca, #6366f1)', color: '#fff', border: 'none', borderRadius: 10, cursor: 'pointer', fontSize: 14, fontWeight: 600, boxShadow: '0 2px 8px rgba(79,70,229,0.2)' }}
          >
            搜索
          </button>
        </div>

        {/* Status filter tabs */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          {FILTER_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setStatusFilter(tab.key)}
              style={{
                padding: '6px 16px',
                border: `1.5px solid ${statusFilter === tab.key ? '#4f46e5' : '#e2e8f0'}`,
                borderRadius: 20,
                background: statusFilter === tab.key ? '#4f46e5' : '#fff',
                color: statusFilter === tab.key ? '#fff' : '#64748b',
                fontSize: 12,
                fontWeight: statusFilter === tab.key ? 600 : 400,
                cursor: 'pointer',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Patient list */}
        {loading ? (
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: 48 }}>加载中...</div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: 48, fontSize: 14 }}>
            {searchQuery ? '未找到匹配的患者' : '暂无患者挂号到您的科室'}
          </div>
        ) : (
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr auto', padding: '12px 18px', background: '#f8fafc', fontSize: 12, color: '#64748b', fontWeight: 600 }}>
              <span>姓名</span>
              <span>手机号</span>
              <span>挂号日期</span>
              <span>状态</span>
              <span>操作</span>
              <span></span>
            </div>
            {filtered.map((p) => {
              const isDeleted = !!p.deleted_at
              const regTransitions = isDeleted ? [] : (TRANSITIONS[p.registration_status] || [])
              return (
                <div
                  key={p.id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr auto',
                    padding: '14px 18px',
                    borderTop: '1px solid #f1f5f9',
                    alignItems: 'center',
                    fontSize: 14,
                    background: isDeleted ? '#fef2f2' : undefined,
                  }}
                >
                  <span style={{ fontWeight: 500, color: isDeleted ? '#94a3b8' : '#1e293b' }}>{p.name}</span>
                  <span style={{ color: '#94a3b8' }}>{maskPhone(p.phone)}</span>
                  <span style={{ color: '#94a3b8' }}>{p.registration_date?.slice(0, 10)}</span>
                  <span>
                    {isDeleted ? (
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 10px',
                        borderRadius: 6,
                        background: '#ef4444',
                        color: '#fff',
                        fontSize: 12,
                        fontWeight: 600,
                      }}>
                        用户已注销
                      </span>
                    ) : (
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 10px',
                        borderRadius: 6,
                        background: STATUS_COLORS[p.registration_status] || '#94a3b8',
                        color: '#fff',
                        fontSize: 12,
                        fontWeight: 600,
                      }}>
                        {STATUS_LABELS[p.registration_status] || p.registration_status}
                      </span>
                    )}
                  </span>
                  <span>
                    {isDeleted ? (
                      <button
                        onClick={() => handleDismissDeleted(p.id)}
                        style={{ padding: '4px 12px', border: '1.5px solid #fca5a5', borderRadius: 6, background: '#fff', color: '#ef4444', cursor: 'pointer', fontSize: 12, fontWeight: 500 }}
                      >
                        清除
                      </button>
                    ) : (
                      <span style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {regTransitions.map((t) => (
                          <button
                            key={t.target}
                            onClick={() => handleStatusTransition(p.id, t.target)}
                            style={{ padding: '4px 12px', border: `1.5px solid ${t.color}`, borderRadius: 6, background: '#fff', color: t.color, cursor: 'pointer', fontSize: 12, fontWeight: 500 }}
                          >
                            {t.label}
                          </button>
                        ))}
                      </span>
                    )}
                  </span>
                  {isDeleted ? (
                  <span style={{ fontSize: 12, color: '#cbd5e1' }}>--</span>
                  ) : (p.registration_status === 'in_consultation' || p.registration_status === 'recovering' || p.registration_status === 'recovered') ? (
                  <button
                    onClick={() => navigate(`/doctor/patient/${p.id}`)}
                    style={{ padding: '6px 14px', background: '#fff', border: '1.5px solid #c7d2fe', borderRadius: 6, color: '#4f46e5', cursor: 'pointer', fontSize: 12, fontWeight: 500, whiteSpace: 'nowrap' }}
                  >
                    查看病历
                  </button>
                  ) : (
                  <span style={{ fontSize: 12, color: '#cbd5e1' }}>--</span>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
