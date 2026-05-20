import { useState, useEffect } from 'react'
import { fetchPatientCarePlans, createCarePlan, updateCarePlan } from '../../api/doctor'
import type { CarePlanItemData, CarePlanCreateData } from '../../types'

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  active: { color: '#52c41a', label: '进行中' },
  completed: { color: '#999', label: '已完成' },
  paused: { color: '#fa8c16', label: '暂停' },
}

interface Props {
  patientId: number
  editable: boolean
}

export default function CarePlanManager({ patientId, editable }: Props) {
  const [plans, setPlans] = useState<CarePlanItemData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [form, setForm] = useState<CarePlanCreateData>({
    title: '',
    description: '',
    medication_schedule: '',
    follow_up_date: '',
  })
  const [creating, setCreating] = useState(false)
  const [msg, setMsg] = useState('')

  const [editingPlanId, setEditingPlanId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<CarePlanCreateData>({ title: '', description: '', medication_schedule: '', follow_up_date: '' })
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    setError('')
    fetchPatientCarePlans(patientId)
      .then((data) => setPlans(data.plans))
      .catch((err) => setError('加载失败: ' + (err.message || '未知错误')))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [patientId])

  const handleCreate = async () => {
    if (!form.title.trim()) {
      setMsg('请输入计划标题')
      return
    }
    setCreating(true)
    setMsg('')
    try {
      const created = await createCarePlan(patientId, form)
      setPlans((prev) => [created, ...prev])
      setForm({ title: '', description: '', medication_schedule: '', follow_up_date: '' })
      setMsg('康复计划创建成功')
    } catch (err: any) {
      setMsg('创建失败: ' + (err.message || '未知错误'))
    } finally {
      setCreating(false)
    }
  }

  const handleStatusChange = async (planId: number, status: string) => {
    try {
      const updated = await updateCarePlan(planId, { status })
      setPlans((prev) => prev.map((p) => (p.id === planId ? updated : p)))
    } catch {
      setError('状态更新失败')
    }
  }

  const startEdit = (plan: CarePlanItemData) => {
    setEditingPlanId(plan.id)
    setEditForm({
      title: plan.title,
      description: plan.description || '',
      medication_schedule: plan.medication_schedule || '',
      follow_up_date: plan.follow_up_date || '',
    })
  }

  const handleEditSave = async () => {
    if (!editingPlanId || !editForm.title.trim()) return
    setSaving(true)
    try {
      const updated = await updateCarePlan(editingPlanId, editForm)
      setPlans((prev) => prev.map((p) => (p.id === editingPlanId ? updated : p)))
      setEditingPlanId(null)
    } catch (err: any) {
      setError('更新失败: ' + (err.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  const fieldStyle: React.CSSProperties = {
    width: '100%',
    padding: '8px 12px',
    border: '1px solid #d9d9d9',
    borderRadius: 6,
    fontSize: 14,
    marginBottom: 12,
  }

  const sectionTitle: React.CSSProperties = {
    fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#333',
  }

  return (
    <div style={{ padding: 16, background: '#fff', borderRadius: 8, border: '1px solid #e8e8e8', marginTop: 16 }}>
      <div style={sectionTitle}>康复计划管理</div>

      {/* Create Form */}
      {editable && (
      <div style={{ marginBottom: 24, padding: 16, background: '#fafafa', borderRadius: 8 }}>
        <div style={{ fontWeight: 600, fontSize: 14, color: '#555', marginBottom: 12 }}>新建康复计划</div>
        {msg && (
          <div style={{
            padding: '6px 12px', marginBottom: 12, borderRadius: 6, fontSize: 13,
            background: msg.includes('成功') ? '#f6ffed' : '#fff2f0',
            color: msg.includes('成功') ? '#52c41a' : '#ff4d4f',
          }}>
            {msg}
          </div>
        )}
        <input
          type="text"
          placeholder="计划标题 *"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={fieldStyle}
        />
        <textarea
          placeholder="计划描述"
          value={form.description || ''}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          rows={3}
          style={{ ...fieldStyle, resize: 'vertical', fontFamily: 'inherit' }}
        />
        <input
          type="text"
          placeholder="用药计划"
          value={form.medication_schedule || ''}
          onChange={(e) => setForm({ ...form, medication_schedule: e.target.value })}
          style={fieldStyle}
        />
        <input
          type="date"
          placeholder="复诊日期"
          value={form.follow_up_date || ''}
          onChange={(e) => setForm({ ...form, follow_up_date: e.target.value })}
          style={fieldStyle}
        />
        <button
          onClick={handleCreate}
          disabled={creating}
          style={{
            padding: '6px 24px',
            background: creating ? '#91caff' : '#1677ff',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontSize: 14,
            cursor: creating ? 'not-allowed' : 'pointer',
          }}
        >
          {creating ? '创建中...' : '创建计划'}
        </button>
      </div>
      )}

      {/* Plan List */}
      {loading && <div style={{ textAlign: 'center', color: '#999', padding: 16 }}>加载中...</div>}
      {error && <div style={{ padding: '8px 12px', background: '#fff2f0', borderRadius: 6, color: '#ff4d4f', fontSize: 13, marginBottom: 12 }}>{error}</div>}
      {!loading && plans.length === 0 && (
        <div style={{ textAlign: 'center', color: '#999', padding: 16 }}>暂无康复计划</div>
      )}
      {plans.map((plan) => {
        const st = STATUS_MAP[plan.status] || STATUS_MAP.active
        const isEditing = editingPlanId === plan.id
        return (
          <div
            key={plan.id}
            style={{
              padding: 12,
              marginBottom: 8,
              borderRadius: 6,
              border: '1px solid #e8e8e8',
              background: isEditing ? '#fffbe6' : '#fafafa',
            }}
          >
            {isEditing ? (
              <div>
                <div style={{ fontWeight: 600, fontSize: 14, color: '#555', marginBottom: 10 }}>编辑康复计划</div>
                <input type="text" placeholder="计划标题 *" value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  style={{ ...fieldStyle, marginBottom: 8 }} />
                <textarea placeholder="计划描述" value={editForm.description || ''}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  rows={2} style={{ ...fieldStyle, resize: 'vertical', fontFamily: 'inherit', marginBottom: 8 }} />
                <input type="text" placeholder="用药计划" value={editForm.medication_schedule || ''}
                  onChange={(e) => setEditForm({ ...editForm, medication_schedule: e.target.value })}
                  style={{ ...fieldStyle, marginBottom: 8 }} />
                <input type="date" placeholder="复诊日期" value={editForm.follow_up_date || ''}
                  onChange={(e) => setEditForm({ ...editForm, follow_up_date: e.target.value })}
                  style={{ ...fieldStyle, marginBottom: 12 }} />
                <div style={{ display: 'flex', gap: 8 }}>
                  <button onClick={handleEditSave} disabled={saving}
                    style={{ padding: '4px 16px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>
                    {saving ? '保存中...' : '保存'}
                  </button>
                  <button onClick={() => setEditingPlanId(null)}
                    style={{ padding: '4px 16px', background: '#fff', border: '1px solid #d9d9d9', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>
                    取消
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 14, color: '#333' }}>{plan.title}</span>
                  <span style={{
                    padding: '0 8px', borderRadius: 4, fontSize: 12, fontWeight: 600,
                    background: st.color + '20', color: st.color,
                  }}>
                    {st.label}
                  </span>
                </div>
                {plan.description && (
                  <div style={{ fontSize: 13, color: '#666', marginBottom: 4, lineHeight: 1.5 }}>{plan.description}</div>
                )}
                {plan.medication_schedule && (
                  <div style={{ fontSize: 13, color: '#333', marginBottom: 4 }}>用药: {plan.medication_schedule}</div>
                )}
                {plan.follow_up_date && (
                  <div style={{ fontSize: 12, color: '#1677ff', marginBottom: 6 }}>复诊: {plan.follow_up_date}</div>
                )}
                {editable && (
                <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                  <button onClick={() => startEdit(plan)}
                    style={{ padding: '2px 10px', border: '1px solid #1677ff', borderRadius: 4, background: '#fff', color: '#1677ff', cursor: 'pointer', fontSize: 12 }}>
                    编辑
                  </button>
                  {plan.status !== 'active' && (
                    <button onClick={() => handleStatusChange(plan.id, 'active')}
                      style={{ padding: '2px 10px', border: '1px solid #52c41a', borderRadius: 4, background: '#fff', color: '#52c41a', cursor: 'pointer', fontSize: 12 }}>
                      设为进行中
                    </button>
                  )}
                  {plan.status !== 'completed' && (
                    <button onClick={() => handleStatusChange(plan.id, 'completed')}
                      style={{ padding: '2px 10px', border: '1px solid #d9d9d9', borderRadius: 4, background: '#fff', color: '#999', cursor: 'pointer', fontSize: 12 }}>
                      设为已完成
                    </button>
                  )}
                  {plan.status !== 'paused' && (
                    <button onClick={() => handleStatusChange(plan.id, 'paused')}
                      style={{ padding: '2px 10px', border: '1px solid #fa8c16', borderRadius: 4, background: '#fff', color: '#fa8c16', cursor: 'pointer', fontSize: 12 }}>
                      暂停
                    </button>
                  )}
                </div>
                )}
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}
