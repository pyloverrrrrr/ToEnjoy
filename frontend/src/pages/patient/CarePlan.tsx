import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { fetchCarePlan } from '../../api/patient'
import type { CarePlanEpisodeData } from '../../types'

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  active: { color: '#52c41a', label: '进行中' },
  completed: { color: '#999', label: '已完成' },
  paused: { color: '#fa8c16', label: '暂停' },
}

const EP_STATUS_LABELS: Record<string, string> = {
  registered: '已挂号', in_consultation: '问诊中', recovering: '康复中',
  recovered: '已康复', need_reregister: '未到请重新挂号', legacy: '历史记录',
}
const EP_STATUS_COLORS: Record<string, string> = {
  registered: '#e11d48', in_consultation: '#10b981', recovering: '#f59e0b',
  recovered: '#94a3b8', need_reregister: '#ef4444', legacy: '#94a3b8',
}

export default function CarePlan() {
  const [data, setData] = useState<CarePlanEpisodeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    if (!token) { navigate('/login'); return }
    setLoading(true)
    fetchCarePlan()
      .then((d) => {
        setData(d)
        if (d.episodes.length > 0) setExpanded(new Set([d.episodes[0].registration_id]))
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [token])

  const toggle = (regId: number) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(regId)) next.delete(regId); else next.add(regId)
      return next
    })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#fef2f2' }}>
      <header style={{ background: '#fff1f2', padding: '14px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #fecdd3' }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#e11d48' }}>康复计划</h2>
          <button onClick={() => navigate('/patient/chat')} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#e11d48', fontWeight: 500 }}>返回对话</button>
          <button onClick={() => navigate('/patient/history')} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#64748b' }}>对话历史</button>
          <button onClick={() => navigate('/patient/medical-record')} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#64748b' }}>我的病历</button>
        </div>
        <button onClick={() => { logout(); navigate('/login') }} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: 'transparent', color: '#64748b', cursor: 'pointer', fontSize: 13 }}>退出</button>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 16px', maxWidth: 700, margin: '0 auto', width: '100%' }}>
        {loading && <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>加载中...</div>}
        {!loading && (!data || data.episodes.length === 0) && (
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>暂无康复计划</div>
        )}

        {data && data.episodes.map((ep) => {
          const isExpanded = expanded.has(ep.registration_id)
          const isLegacy = ep.status === 'legacy'
          return (
            <div key={ep.registration_id} style={{ border: '1px solid #fecdd3', borderRadius: 12, marginBottom: 12, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
              <div onClick={() => toggle(ep.registration_id)} style={{
                padding: '12px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                cursor: 'pointer', background: '#fff1f2', borderBottom: isExpanded ? '1px solid #fecdd3' : 'none',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 18, color: isExpanded ? '#e11d48' : '#94a3b8' }}>{isExpanded ? '▼' : '▶'}</span>
                  {isLegacy ? (
                    <span style={{ fontWeight: 600, fontSize: 14, color: '#94a3b8' }}>历史记录</span>
                  ) : (
                    <>
                      <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: 6, background: '#e11d48', color: '#fff', fontSize: 12, fontWeight: 600 }}>序号{ep.sequence_number}</span>
                      <span style={{ fontSize: 13, color: '#64748b' }}>{ep.department}</span>
                      <span style={{ fontSize: 12, color: '#94a3b8' }}>{ep.registration_date?.slice(0, 10)}</span>
                    </>
                  )}
                </div>
                <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: 6, background: EP_STATUS_COLORS[ep.status] || '#94a3b8', color: '#fff', fontSize: 12, fontWeight: 600 }}>
                  {EP_STATUS_LABELS[ep.status] || ep.status}
                </span>
              </div>

              {isExpanded && (
                <div style={{ padding: '16px 18px', background: '#fff' }}>
                  {ep.plans.length === 0 && <div style={{ color: '#94a3b8', fontSize: 13 }}>暂无康复计划</div>}
                  {ep.plans.map((plan) => {
                    const st = STATUS_MAP[plan.status] || STATUS_MAP.active
                    return (
                      <div key={plan.id} style={{ background: '#fff', padding: 16, borderRadius: 10, marginBottom: 8, border: '1px solid #f1f5f9', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <span style={{ fontWeight: 600, fontSize: 15, color: '#1e293b' }}>{plan.title}</span>
                          <span style={{ padding: '2px 10px', borderRadius: 6, background: st.color + '20', color: st.color, fontSize: 12, fontWeight: 600 }}>{st.label}</span>
                        </div>
                        {plan.description && <div style={{ fontSize: 13, color: '#64748b', marginBottom: 8, lineHeight: 1.6 }}>{plan.description}</div>}
                        {plan.medication_schedule && (
                          <div style={{ fontSize: 13, color: '#334155', marginBottom: 4, background: '#f8fafc', padding: '10px 14px', borderRadius: 8, border: '1px solid #f1f5f9' }}>
                            <span style={{ fontWeight: 600 }}>用药计划: </span>{plan.medication_schedule}
                          </div>
                        )}
                        {plan.follow_up_date && <div style={{ fontSize: 12, color: '#e11d48', fontWeight: 500 }}>复诊日期: {plan.follow_up_date}</div>}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
