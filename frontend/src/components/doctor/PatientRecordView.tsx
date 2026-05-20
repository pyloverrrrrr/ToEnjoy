import { useState } from 'react'
import type { PatientRecordData, CarePlanItemData } from '../../types'

interface Props {
  patient: PatientRecordData
  editable: boolean
  activeRegistrationId: number | null
  onCreateCase: (regId: number, data: Record<string, string>) => Promise<void>
  onCreateVisit: (regId: number, data: Record<string, string>) => Promise<void>
  onCreatePrescription: (regId: number, data: Record<string, string>) => Promise<void>
  onCreateCarePlan: (regId: number, data: Record<string, string>) => Promise<void>
  onUpdateCase: (id: number, data: Record<string, string>) => Promise<void>
  onDeleteCase: (id: number) => Promise<void>
  onUpdateVisit: (id: number, data: Record<string, string>) => Promise<void>
  onDeleteVisit: (id: number) => Promise<void>
  onUpdatePrescription: (id: number, data: Record<string, string>) => Promise<void>
  onDeletePrescription: (id: number) => Promise<void>
  onUpdateCarePlan: (id: number, data: Record<string, string>) => Promise<void>
  onDeleteCarePlan: (id: number) => Promise<void>
}

const STATUS_LABELS: Record<string, string> = {
  registered: '已挂号', in_consultation: '问诊中', recovering: '康复中',
  recovered: '已康复', need_reregister: '未到请重新挂号', legacy: '历史记录', mock: '模拟数据',
}

const STATUS_COLORS: Record<string, string> = {
  registered: '#4f46e5', in_consultation: '#10b981', recovering: '#f59e0b',
  recovered: '#94a3b8', need_reregister: '#ef4444', legacy: '#94a3b8', mock: '#94a3b8',
}

const labelStyle: React.CSSProperties = { color: '#94a3b8', fontSize: 12, fontWeight: 500 }
const smallBtn: React.CSSProperties = { padding: '2px 10px', border: '1.5px solid #e2e8f0', borderRadius: 6, background: '#fff', cursor: 'pointer', fontSize: 12, marginLeft: 6, fontWeight: 500 }

function AddForm({ fields, onSave, onCancel }: { fields: string[]; onSave: (d: Record<string, string>) => void; onCancel: () => void }) {
  const [data, setData] = useState<Record<string, string>>({})
  return (
    <div style={{ background: '#f0f5ff', padding: 10, borderRadius: 4, marginBottom: 8 }}>
      {fields.map((f) => (
        <div key={f} style={{ marginBottom: 6 }}>
          <span style={{ fontSize: 11, color: '#666', display: 'block', marginBottom: 2 }}>{f}</span>
          <input value={data[f] || ''} onChange={(e) => setData({ ...data, [f]: e.target.value })}
            style={{ width: '100%', padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 12, boxSizing: 'border-box' }} />
        </div>
      ))}
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <button onClick={() => onSave(data)} style={{ padding: '3px 12px', background: '#4f46e5', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>保存</button>
        <button onClick={onCancel} style={{ padding: '3px 12px', background: '#fff', border: '1px solid #d9d9d9', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>取消</button>
      </div>
    </div>
  )
}

function EditForm({ fields, fieldKeys, initialData, onSave, onCancel }: { fields: string[]; fieldKeys: string[]; initialData: Record<string, unknown>; onSave: (d: Record<string, string>) => void; onCancel: () => void }) {
  const [data, setData] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {}
    fields.forEach((f, i) => { init[f] = (initialData[fieldKeys[i]] as string) || '' })
    return init
  })
  return (
    <div style={{ background: '#fffbe6', padding: 10, borderRadius: 4, marginBottom: 8, border: '1px solid #ffe58f' }}>
      {fields.map((f) => (
        <div key={f} style={{ marginBottom: 6 }}>
          <span style={{ fontSize: 11, color: '#666', display: 'block', marginBottom: 2 }}>{f}</span>
          <input value={data[f] || ''} onChange={(e) => setData({ ...data, [f]: e.target.value })}
            style={{ width: '100%', padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 12, boxSizing: 'border-box' }} />
        </div>
      ))}
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <button onClick={() => onSave(data)} style={{ padding: '3px 12px', background: '#4f46e5', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>保存</button>
        <button onClick={onCancel} style={{ padding: '3px 12px', background: '#fff', border: '1px solid #d9d9d9', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>取消</button>
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  if (!value) return null
  return <div><span style={labelStyle}>{label}: </span><span style={{ color: '#1e293b' }}>{value}</span></div>
}

function EditableCarePlanList({
  plans, canEdit, onAdd, onUpdate, onDelete, editingId, setEditingId, deleting,
}: {
  plans: CarePlanItemData[]
  canEdit: boolean
  onAdd: () => void
  onUpdate: (id: number, data: Record<string, string>) => Promise<void>
  onDelete: (id: number) => Promise<void>
  editingId: number | null
  setEditingId: (id: number | null) => void
  deleting: number | null
}) {
  const CARE_COLORS: Record<string, string> = { active: '#52c41a', completed: '#999', paused: '#fa8c16' }
  const CARE_LABELS: Record<string, string> = { active: '进行中', completed: '已完成', paused: '暂停' }

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontWeight: 600, fontSize: 13, color: '#475569' }}>康复计划 ({plans.length})</span>
        {canEdit && (
          <button onClick={onAdd}
            style={{ padding: '2px 10px', border: '1px solid #4f46e5', borderRadius: 4, background: '#fff', cursor: 'pointer', fontSize: 12, color: '#4f46e5' }}>
            + 新增
          </button>
        )}
      </div>
      {plans.length === 0 && <div style={{ color: '#bbb', fontSize: 12 }}>暂无</div>}
      {plans.map((plan) => (
        <div key={plan.id} style={{ background: '#fafafa', padding: '8px 10px', borderRadius: 4, marginBottom: 4, fontSize: 12, border: '1px solid #f0f0f0' }}>
          {editingId === plan.id ? (
            <EditForm
              fields={['标题', '说明', '用药计划', '复诊日期', '状态']}
              fieldKeys={['title', 'description', 'medication_schedule', 'follow_up_date', 'status']}
              initialData={plan as unknown as Record<string, unknown>}
              onSave={async (d) => { await onUpdate(plan.id, { title: d['标题'], description: d['说明'], medication_schedule: d['用药计划'], follow_up_date: d['复诊日期'], status: d['状态'] }); setEditingId(null) }}
              onCancel={() => setEditingId(null)}
            />
          ) : (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 500 }}>{plan.title}</span>
                  <span style={{ fontSize: 11, padding: '0 6px', borderRadius: 3, background: (CARE_COLORS[plan.status] || '#999') + '20', color: CARE_COLORS[plan.status] || '#999', fontWeight: 500 }}>
                    {CARE_LABELS[plan.status] || plan.status}
                  </span>
                </div>
                {plan.description && <div style={{ color: '#666', marginTop: 2 }}>{plan.description}</div>}
                {plan.medication_schedule && <div style={{ color: '#1e293b', marginTop: 2 }}>用药: {plan.medication_schedule}</div>}
                {plan.follow_up_date && <div style={{ color: '#4f46e5', marginTop: 2 }}>复诊: {plan.follow_up_date}</div>}
              </div>
              {canEdit && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginLeft: 8 }}>
                  <button onClick={() => setEditingId(plan.id)} style={{ ...smallBtn, color: '#4f46e5', borderColor: '#4f46e5' }}>编辑</button>
                  <button onClick={() => { onDelete(plan.id) }} disabled={deleting === plan.id}
                    style={{ ...smallBtn, color: '#ff4d4f', borderColor: '#ffccc7' }}>
                    {deleting === plan.id ? '...' : '删除'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default function PatientRecordView({
  patient, editable, activeRegistrationId,
  onCreateCase, onCreateVisit, onCreatePrescription, onCreateCarePlan,
  onUpdateCase, onDeleteCase, onUpdateVisit, onDeleteVisit,
  onUpdatePrescription, onDeletePrescription,
  onUpdateCarePlan, onDeleteCarePlan,
}: Props) {
  const [expandedEpisodes, setExpandedEpisodes] = useState<Set<number>>(() => {
    // Auto-expand active episodes by default
    const active = new Set<number>()
    patient.episodes.forEach((ep) => {
      if (['registered', 'in_consultation', 'recovering'].includes(ep.status)) {
        active.add(ep.registration_id)
      }
    })
    return active
  })

  const [showCaseForm, setShowCaseForm] = useState<number | null>(null)
  const [showVisitForm, setShowVisitForm] = useState<number | null>(null)
  const [showRxForm, setShowRxForm] = useState<number | null>(null)
  const [showCarePlanForm, setShowCarePlanForm] = useState<number | null>(null)
  const [editingCaseId, setEditingCaseId] = useState<number | null>(null)
  const [editingVisitId, setEditingVisitId] = useState<number | null>(null)
  const [editingRxId, setEditingRxId] = useState<number | null>(null)
  const [editingCarePlanId, setEditingCarePlanId] = useState<number | null>(null)
  const [deleting, setDeleting] = useState<number | null>(null)

  const toggleEpisode = (regId: number) => {
    setExpandedEpisodes((prev) => {
      const next = new Set(prev)
      if (next.has(regId)) next.delete(regId)
      else next.add(regId)
      return next
    })
  }

  const handleDelete = async (id: number, fn: (id: number) => Promise<void>) => {
    if (deleting === id) return
    setDeleting(id)
    try { await fn(id) } finally { setDeleting(null) }
  }

  return (
    <div style={{ padding: 16, background: '#fff', borderRadius: 8, border: '1px solid #e8e8e8', marginBottom: 16 }}>
      <div style={{ fontWeight: 600, fontSize: 16, color: '#1e293b', marginBottom: 16 }}>
        患者记录: {patient.patient_name || '未知'}
      </div>

      {/* Basic Info */}
      <div style={{ background: '#fafafa', padding: 10, borderRadius: 4, marginBottom: 12, fontSize: 13, lineHeight: 1.6 }}>
        <div><span style={labelStyle}>ID: </span><span style={{ color: '#1e293b' }}>{patient.patient_id}</span></div>
        <div><span style={labelStyle}>姓名: </span><span style={{ color: '#1e293b' }}>{patient.patient_name || '-'}</span></div>
        <div><span style={labelStyle}>角色: </span><span style={{ color: '#1e293b' }}>{patient.patient_role || '-'}</span></div>
      </div>

      {/* Episodes */}
      {patient.episodes.length === 0 && (
        <div style={{ textAlign: 'center', color: '#999', padding: 24 }}>暂无病历记录</div>
      )}

      {patient.episodes.map((ep) => {
        const isExpanded = expandedEpisodes.has(ep.registration_id)
        const isActive = ['registered', 'in_consultation', 'recovering'].includes(ep.status)
        const isLegacy = ep.status === 'legacy' || ep.status === 'mock'
        const canEdit = editable && isActive && activeRegistrationId === ep.registration_id

        return (
          <div key={ep.registration_id} style={{ border: '1px solid #e8e8e8', borderRadius: 8, marginBottom: 12, overflow: 'hidden' }}>
            {/* Episode Header */}
            <div
              onClick={() => toggleEpisode(ep.registration_id)}
              style={{
                padding: '10px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                cursor: 'pointer', background: isActive ? '#f6ffed' : '#fafafa',
                borderBottom: isExpanded ? '1px solid #f0f0f0' : 'none',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 18, color: isExpanded ? '#4f46e5' : '#999' }}>
                  {isExpanded ? '▼' : '▶'}
                </span>
                {isLegacy ? (
                  <span style={{ fontWeight: 600, fontSize: 14, color: '#999' }}>历史记录</span>
                ) : (
                  <>
                    <span style={{
                      display: 'inline-block', padding: '2px 10px', borderRadius: 4,
                      background: '#4f46e5', color: '#fff', fontSize: 12, fontWeight: 600,
                    }}>
                      序号{ep.sequence_number}
                    </span>
                    <span style={{ fontSize: 13, color: '#666' }}>{ep.department}</span>
                    <span style={{ fontSize: 12, color: '#999' }}>{ep.registration_date?.slice(0, 10)}</span>
                  </>
                )}
              </div>
              <span style={{
                display: 'inline-block', padding: '2px 10px', borderRadius: 4,
                background: STATUS_COLORS[ep.status] || '#999', color: '#fff', fontSize: 12, fontWeight: 500,
              }}>
                {STATUS_LABELS[ep.status] || ep.status}
              </span>
            </div>

            {/* Episode Body */}
            {isExpanded && (
              <div style={{ padding: '12px 16px' }}>
                {/* Cases */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#475569' }}>病例记录 ({ep.cases.length})</span>
                    {canEdit && (
                      <button onClick={(e) => { e.stopPropagation(); setShowCaseForm(showCaseForm === ep.registration_id ? null : ep.registration_id) }}
                        style={{ padding: '2px 10px', border: '1px solid #4f46e5', borderRadius: 4, background: '#fff', cursor: 'pointer', fontSize: 12, color: '#4f46e5' }}>
                        + 新增
                      </button>
                    )}
                  </div>
                  {showCaseForm === ep.registration_id && (
                    <AddForm fields={['诊断', '治疗方案', '过敏史', '出院小结']}
                      onSave={async (d) => { await onCreateCase(ep.registration_id, { diagnosis: d['诊断'], procedures: d['治疗方案'], allergies: d['过敏史'], discharge_summary: d['出院小结'] }); setShowCaseForm(null) }}
                      onCancel={() => setShowCaseForm(null)} />
                  )}
                  {ep.cases.length === 0 && <div style={{ color: '#bbb', fontSize: 12 }}>暂无</div>}
                  {ep.cases.map((c, i) => (
                    <div key={i} style={{ background: '#fafafa', padding: 10, borderRadius: 4, marginBottom: 6, fontSize: 13, lineHeight: 1.6 }}>
                      {editingCaseId === (c.id as number) ? (
                        <EditForm fields={['诊断', '治疗方案', '过敏史', '出院小结']}
                          fieldKeys={['diagnosis', 'procedures', 'allergies', 'discharge_summary']} initialData={c}
                          onSave={async (d) => { await onUpdateCase(c.id as number, { diagnosis: d['诊断'], procedures: d['治疗方案'], allergies: d['过敏史'], discharge_summary: d['出院小结'] }); setEditingCaseId(null) }}
                          onCancel={() => setEditingCaseId(null)} />
                      ) : (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ flex: 1 }}>
                            <InfoRow label="诊断" value={c.diagnosis as string || ''} />
                            <InfoRow label="治疗方案" value={c.procedures as string || ''} />
                            <InfoRow label="过敏史" value={c.allergies as string || ''} />
                            <InfoRow label="出院小结" value={c.discharge_summary as string || ''} />
                          </div>
                          {canEdit && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginLeft: 8 }}>
                              <button onClick={() => setEditingCaseId(c.id as number)} style={{ ...smallBtn, color: '#4f46e5', borderColor: '#4f46e5' }}>编辑</button>
                              <button onClick={() => handleDelete(c.id as number, onDeleteCase)} disabled={deleting === (c.id as number)}
                                style={{ ...smallBtn, color: '#ff4d4f', borderColor: '#ffccc7' }}>
                                {deleting === (c.id as number) ? '...' : '删除'}
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Visits */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#475569' }}>就诊记录 ({ep.visits.length})</span>
                    {canEdit && (
                      <button onClick={(e) => { e.stopPropagation(); setShowVisitForm(showVisitForm === ep.registration_id ? null : ep.registration_id) }}
                        style={{ padding: '2px 10px', border: '1px solid #4f46e5', borderRadius: 4, background: '#fff', cursor: 'pointer', fontSize: 12, color: '#4f46e5' }}>
                        + 新增
                      </button>
                    )}
                  </div>
                  {showVisitForm === ep.registration_id && (
                    <AddForm fields={['就诊日期', '科室', '医生', '主诉', '诊断']}
                      onSave={async (d) => { await onCreateVisit(ep.registration_id, { visit_date: d['就诊日期'], department: d['科室'], doctor_name: d['医生'], chief_complaint: d['主诉'], diagnosis: d['诊断'] }); setShowVisitForm(null) }}
                      onCancel={() => setShowVisitForm(null)} />
                  )}
                  {ep.visits.length === 0 && <div style={{ color: '#bbb', fontSize: 12 }}>暂无</div>}
                  {ep.visits.map((v, i) => (
                    <div key={i} style={{ background: '#fafafa', padding: 10, borderRadius: 4, marginBottom: 6, fontSize: 13, lineHeight: 1.6 }}>
                      {editingVisitId === (v.id as number) ? (
                        <EditForm fields={['就诊日期', '科室', '医生', '主诉', '诊断']}
                          fieldKeys={['visit_date', 'department', 'doctor_name', 'chief_complaint', 'diagnosis']} initialData={v}
                          onSave={async (d) => { await onUpdateVisit(v.id as number, { visit_date: d['就诊日期'], department: d['科室'], doctor_name: d['医生'], chief_complaint: d['主诉'], diagnosis: d['诊断'] }); setEditingVisitId(null) }}
                          onCancel={() => setEditingVisitId(null)} />
                      ) : (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ flex: 1 }}>
                            <InfoRow label="就诊日期" value={v.visit_date as string || ''} />
                            <InfoRow label="科室" value={v.department as string || ''} />
                            <InfoRow label="医生" value={v.doctor_name as string || ''} />
                            <InfoRow label="主诉" value={v.chief_complaint as string || ''} />
                            <InfoRow label="诊断" value={v.diagnosis as string || ''} />
                          </div>
                          {canEdit && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginLeft: 8 }}>
                              <button onClick={() => setEditingVisitId(v.id as number)} style={{ ...smallBtn, color: '#4f46e5', borderColor: '#4f46e5' }}>编辑</button>
                              <button onClick={() => handleDelete(v.id as number, onDeleteVisit)} disabled={deleting === (v.id as number)}
                                style={{ ...smallBtn, color: '#ff4d4f', borderColor: '#ffccc7' }}>
                                {deleting === (v.id as number) ? '...' : '删除'}
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Prescriptions */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#475569' }}>处方记录 ({ep.prescriptions.length})</span>
                    {canEdit && (
                      <button onClick={(e) => { e.stopPropagation(); setShowRxForm(showRxForm === ep.registration_id ? null : ep.registration_id) }}
                        style={{ padding: '2px 10px', border: '1px solid #4f46e5', borderRadius: 4, background: '#fff', cursor: 'pointer', fontSize: 12, color: '#4f46e5' }}>
                        + 新增
                      </button>
                    )}
                  </div>
                  {showRxForm === ep.registration_id && (
                    <AddForm fields={['药品名称', '剂量', '频次', '疗程', '处方日期']}
                      onSave={async (d) => { await onCreatePrescription(ep.registration_id, { drug_name: d['药品名称'], dosage: d['剂量'], frequency: d['频次'], duration: d['疗程'], prescribed_date: d['处方日期'] }); setShowRxForm(null) }}
                      onCancel={() => setShowRxForm(null)} />
                  )}
                  {ep.prescriptions.length === 0 && <div style={{ color: '#bbb', fontSize: 12 }}>暂无</div>}
                  {ep.prescriptions.map((p, i) => (
                    <div key={i} style={{ background: '#fafafa', padding: 10, borderRadius: 4, marginBottom: 6, fontSize: 13, lineHeight: 1.6 }}>
                      {editingRxId === (p.id as number) ? (
                        <EditForm fields={['药品名称', '剂量', '频次', '疗程', '处方日期', '备注']}
                          fieldKeys={['drug_name', 'dosage', 'frequency', 'duration', 'prescribed_date', 'notes']} initialData={p}
                          onSave={async (d) => { await onUpdatePrescription(p.id as number, { drug_name: d['药品名称'], dosage: d['剂量'], frequency: d['频次'], duration: d['疗程'], prescribed_date: d['处方日期'], notes: d['备注'] }); setEditingRxId(null) }}
                          onCancel={() => setEditingRxId(null)} />
                      ) : (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ flex: 1 }}>
                            <InfoRow label="药品" value={p.drug_name as string || ''} />
                            <InfoRow label="剂量" value={p.dosage as string || ''} />
                            <InfoRow label="频次" value={p.frequency as string || ''} />
                            <InfoRow label="疗程" value={p.duration as string || ''} />
                            <InfoRow label="处方日期" value={p.prescribed_date as string || ''} />
                            <InfoRow label="备注" value={p.notes as string || ''} />
                          </div>
                          {canEdit && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginLeft: 8 }}>
                              <button onClick={() => setEditingRxId(p.id as number)} style={{ ...smallBtn, color: '#4f46e5', borderColor: '#4f46e5' }}>编辑</button>
                              <button onClick={() => handleDelete(p.id as number, onDeletePrescription)} disabled={deleting === (p.id as number)}
                                style={{ ...smallBtn, color: '#ff4d4f', borderColor: '#ffccc7' }}>
                                {deleting === (p.id as number) ? '...' : '删除'}
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Care Plans within episode */}
                {showCarePlanForm === ep.registration_id && (
                  <AddForm fields={['标题', '说明', '用药计划', '复诊日期']}
                    onSave={async (d) => { await onCreateCarePlan(ep.registration_id, { title: d['标题'], description: d['说明'], medication_schedule: d['用药计划'], follow_up_date: d['复诊日期'] }); setShowCarePlanForm(null) }}
                    onCancel={() => setShowCarePlanForm(null)} />
                )}
                <EditableCarePlanList
                  plans={(ep.care_plans || []) as CarePlanItemData[]}
                  canEdit={canEdit}
                  onAdd={() => setShowCarePlanForm(showCarePlanForm === ep.registration_id ? null : ep.registration_id)}
                  onUpdate={onUpdateCarePlan}
                  onDelete={async (id) => { await handleDelete(id, onDeleteCarePlan) }}
                  editingId={editingCarePlanId}
                  setEditingId={setEditingCarePlanId}
                  deleting={deleting}
                />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
