import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { fetchMedicalRecords } from '../../api/patient'
import type { MedicalRecordsEpisodeData } from '../../types'

const STATUS_LABELS: Record<string, string> = {
  registered: '已挂号', in_consultation: '问诊中', recovering: '康复中',
  recovered: '已康复', need_reregister: '未到请重新挂号', legacy: '历史记录',
}
const STATUS_COLORS: Record<string, string> = {
  registered: '#e11d48', in_consultation: '#10b981', recovering: '#f59e0b',
  recovered: '#94a3b8', need_reregister: '#ef4444', legacy: '#94a3b8',
}

const labelStyle: React.CSSProperties = { color: '#94a3b8', fontSize: 12, fontWeight: 500 }

function InfoRow({ label, value }: { label: string; value?: string }) {
  if (!value) return null
  return <div style={{ marginBottom: 2 }}><span style={labelStyle}>{label}: </span><span style={{ color: '#334155' }}>{value}</span></div>
}

export default function PatientMedicalRecord() {
  const [data, setData] = useState<MedicalRecordsEpisodeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    if (!token) { navigate('/login'); return }
    fetchMedicalRecords()
      .then((d) => {
        setData(d)
        // Auto-expand first episode
        if (d.episodes.length > 0) setExpanded(new Set([d.episodes[0].registration_id]))
      })
      .catch(() => setData(null))
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
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#e11d48' }}>我的病历</h2>
          <button onClick={() => navigate('/patient/chat')} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#e11d48', fontWeight: 500 }}>返回对话</button>
          <button onClick={() => navigate('/patient/care-plan')} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#64748b' }}>康复计划</button>
        </div>
        <button onClick={() => { logout(); navigate('/login') }} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: 'transparent', color: '#64748b', cursor: 'pointer', fontSize: 13 }}>退出</button>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 16px', maxWidth: 800, margin: '0 auto', width: '100%' }}>
        {loading && <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>加载中...</div>}
        {!loading && !data && <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>暂无病历记录</div>}

        {data && (
          <>
            <div style={{ fontWeight: 600, fontSize: 17, color: '#1e293b', marginBottom: 16 }}>
              {data.patient_name} 的病历档案
            </div>

            {data.episodes.length === 0 && (
              <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>暂无病历记录</div>
            )}

            {data.episodes.map((ep) => {
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
                    <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: 6, background: STATUS_COLORS[ep.status] || '#94a3b8', color: '#fff', fontSize: 12, fontWeight: 600 }}>
                      {STATUS_LABELS[ep.status] || ep.status}
                    </span>
                  </div>

                  {isExpanded && (
                    <div style={{ padding: '16px 18px', background: '#fff' }}>
                      {!isLegacy && ep.status !== 'recovered' && (
                        <div style={{ padding: '8px 14px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 8, color: '#d97706', fontSize: 12, marginBottom: 12 }}>
                          诊疗进行中，病历将在医生确认康复后生成
                        </div>
                      )}
                      <div style={{ marginBottom: 16 }}>
                        <div style={{ fontWeight: 600, fontSize: 14, color: '#475569', marginBottom: 8 }}>病例记录 ({ep.cases.length})</div>
                        {ep.cases.length === 0 && <div style={{ color: '#94a3b8', fontSize: 13 }}>暂无</div>}
                        {ep.cases.map((c, i) => (
                          <div key={i} style={{ background: '#f8fafc', padding: 14, borderRadius: 8, marginBottom: 6, fontSize: 13, lineHeight: 1.7, border: '1px solid #f1f5f9' }}>
                            <InfoRow label="诊断" value={c.diagnosis as string} />
                            <InfoRow label="治疗方案" value={c.procedures as string} />
                            <InfoRow label="过敏史" value={c.allergies as string} />
                            <InfoRow label="出院小结" value={c.discharge_summary as string} />
                          </div>
                        ))}
                      </div>

                      <div style={{ marginBottom: 16 }}>
                        <div style={{ fontWeight: 600, fontSize: 14, color: '#475569', marginBottom: 8 }}>就诊记录 ({ep.visits.length})</div>
                        {ep.visits.length === 0 && <div style={{ color: '#94a3b8', fontSize: 13 }}>暂无</div>}
                        {ep.visits.map((v, i) => (
                          <div key={i} style={{ background: '#f8fafc', padding: 14, borderRadius: 8, marginBottom: 6, fontSize: 13, lineHeight: 1.7, border: '1px solid #f1f5f9' }}>
                            <InfoRow label="就诊日期" value={v.visit_date as string} />
                            <InfoRow label="科室" value={v.department as string} />
                            <InfoRow label="医生" value={v.doctor_name as string} />
                            <InfoRow label="主诉" value={v.chief_complaint as string} />
                            <InfoRow label="诊断" value={v.diagnosis as string} />
                          </div>
                        ))}
                      </div>

                      <div style={{ marginBottom: 16 }}>
                        <div style={{ fontWeight: 600, fontSize: 14, color: '#475569', marginBottom: 8 }}>处方记录 ({ep.prescriptions.length})</div>
                        {ep.prescriptions.length === 0 && <div style={{ color: '#94a3b8', fontSize: 13 }}>暂无</div>}
                        {ep.prescriptions.map((p, i) => (
                          <div key={i} style={{ background: '#f8fafc', padding: 14, borderRadius: 8, marginBottom: 6, fontSize: 13, lineHeight: 1.7, border: '1px solid #f1f5f9' }}>
                            <InfoRow label="药品" value={p.drug_name as string} />
                            <InfoRow label="剂量" value={p.dosage as string} />
                            <InfoRow label="频次" value={p.frequency as string} />
                            <InfoRow label="疗程" value={p.duration as string} />
                            <InfoRow label="处方日期" value={p.prescribed_date as string} />
                            <InfoRow label="备注" value={p.notes as string} />
                          </div>
                        ))}
                      </div>

                      <div style={{ marginBottom: 16 }}>
                        <div style={{ fontWeight: 600, fontSize: 14, color: '#475569', marginBottom: 8 }}>康复计划 ({(ep.care_plans || []).length})</div>
                        {(ep.care_plans || []).length === 0 && <div style={{ color: '#94a3b8', fontSize: 13 }}>暂无</div>}
                        {(ep.care_plans || []).map((plan) => {
                          const CARE_COLORS: Record<string, string> = { active: '#10b981', completed: '#94a3b8', paused: '#f59e0b' }
                          const CARE_LABELS: Record<string, string> = { active: '进行中', completed: '已完成', paused: '暂停' }
                          return (
                            <div key={plan.id} style={{ background: '#f8fafc', padding: 14, borderRadius: 8, marginBottom: 6, fontSize: 13, lineHeight: 1.7, border: '1px solid #f1f5f9' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                                <span style={{ fontWeight: 500, color: '#1e293b' }}>{plan.title}</span>
                                <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: (CARE_COLORS[plan.status] || '#94a3b8') + '20', color: CARE_COLORS[plan.status] || '#94a3b8', fontWeight: 600 }}>
                                  {CARE_LABELS[plan.status] || plan.status}
                                </span>
                              </div>
                              <InfoRow label="说明" value={plan.description as string} />
                              <InfoRow label="用药计划" value={plan.medication_schedule as string} />
                              <InfoRow label="复诊日期" value={plan.follow_up_date as string} />
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </>
        )}
      </div>
    </div>
  )
}
