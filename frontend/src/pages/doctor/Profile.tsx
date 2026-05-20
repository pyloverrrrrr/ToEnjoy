import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { fetchDoctorProfile, updateDoctorProfile } from '../../api/doctor'
import { fetchMe, updateMe, uploadAvatar, changePassword, deleteAccount } from '../../api/auth'
import type { DoctorProfileData, UserMeData } from '../../types'

const ACCENT = '#4f46e5'
const ACCENT_GRADIENT = 'linear-gradient(135deg, #4338ca, #6366f1)'

export default function DoctorProfile() {
  const [profile, setProfile] = useState<DoctorProfileData | null>(null)
  const [userInfo, setUserInfo] = useState<UserMeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  const [form, setForm] = useState({ department: '', title: '', specialty: '', license_no: '' })
  const [editing, setEditing] = useState(false)

  const [userForm, setUserForm] = useState({ phone: '', email: '' })
  const [editingUser, setEditingUser] = useState(false)

  const [pwForm, setPwForm] = useState({ oldPassword: '', newPassword: '', confirmPassword: '' })
  const [changingPw, setChangingPw] = useState(false)
  const [pwMsg, setPwMsg] = useState('')
  const [pwSaving, setPwSaving] = useState(false)

  const [delForm, setDelForm] = useState({ password: '', confirmPassword: '' })
  const [showingDelete, setShowingDelete] = useState(false)
  const [delMsg, setDelMsg] = useState('')
  const [deleting, setDeleting] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  const user = useAuthStore((s) => s.user)
  const updateUser = useAuthStore((s) => s.updateUser)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    if (!token) { navigate('/login'); return }
    setLoading(true)
    Promise.all([
      fetchDoctorProfile().catch(() => null),
      fetchMe().catch(() => null),
    ])
      .then(([p, u]) => {
        setProfile(p)
        if (p) setForm({ department: p.department || '', title: p.title || '', specialty: p.specialty || '', license_no: p.license_no || '' })
        if (u) {
          setUserInfo(u)
          setUserForm({ phone: u.phone || '', email: u.email || '' })
          if (u.avatar_url || u.name) updateUser({ name: u.name, avatar_url: u.avatar_url })
        }
      })
      .catch(() => setMsg('加载失败'))
      .finally(() => setLoading(false))
  }, [token])

  const handleSaveProfessional = async () => {
    setSaving(true); setMsg('')
    try {
      const data: Record<string, string> = {}
      if (form.department) data.department = form.department
      if (form.title) data.title = form.title
      if (form.specialty) data.specialty = form.specialty
      if (form.license_no) data.license_no = form.license_no
      const updated = await updateDoctorProfile(data)
      setProfile(updated); setEditing(false); setMsg('执业信息保存成功')
    } catch { setMsg('保存失败') }
    finally { setSaving(false) }
  }

  const handleSaveUser = async () => {
    setSaving(true); setMsg('')
    try {
      const data: Record<string, string> = {}
      if (userForm.phone) data.phone = userForm.phone
      if (userForm.email) data.email = userForm.email
      const updated = await updateMe(data)
      setUserInfo(updated); updateUser({ name: updated.name, avatar_url: updated.avatar_url })
      setEditingUser(false); setMsg('个人信息保存成功')
    } catch { setMsg('保存失败') }
    finally { setSaving(false) }
  }

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) { setMsg('请选择图片文件'); return }
    try {
      const avatarUrl = await uploadAvatar(file)
      updateUser({ avatar_url: avatarUrl })
      setUserInfo((prev) => prev ? { ...prev, avatar_url: avatarUrl } : prev)
      setMsg('头像更新成功')
    } catch { setMsg('头像上传失败') }
  }

  const handleChangePassword = async () => {
    if (pwForm.newPassword !== pwForm.confirmPassword) { setPwMsg('两次输入的新密码不一致'); return }
    if (pwForm.newPassword.length < 6) { setPwMsg('新密码至少需要6个字符'); return }
    setPwSaving(true); setPwMsg('')
    try {
      await changePassword(pwForm.oldPassword, pwForm.newPassword)
      setPwMsg('密码修改成功'); setPwForm({ oldPassword: '', newPassword: '', confirmPassword: '' }); setChangingPw(false)
    } catch (err: any) { setPwMsg(err.message || '密码修改失败') }
    finally { setPwSaving(false) }
  }

  const handleDeleteAccount = async () => {
    if (delForm.password !== delForm.confirmPassword) { setDelMsg('两次输入的密码不一致'); return }
    if (!delForm.password) { setDelMsg('请输入密码'); return }
    setDeleting(true); setDelMsg('')
    try {
      await deleteAccount(delForm.password, delForm.confirmPassword)
      logout(); navigate('/login')
    } catch (err: any) { setDelMsg(err.message || '注销失败') }
    finally { setDeleting(false) }
  }

  const avatarUrl = userInfo?.avatar_url || user?.avatar_url

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f8fafc' }}>
      <header style={{
        background: ACCENT_GRADIENT,
        padding: '14px 28px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 12px rgba(79,70,229,0.2)',
      }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, fontWeight: 700, color: '#fff' }}>R</div>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#fff' }}>医生档案</h2>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={() => navigate('/doctor/chat')} style={{
            padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
            background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13,
          }}>返回问诊</button>
          <button onClick={() => navigate('/doctor/patients')} style={{
            padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
            background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13,
          }}>患者列表</button>
          <button onClick={() => navigate('/doctor/search')} style={{
            padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
            background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13,
          }}>知识检索</button>
          <button onClick={() => { logout(); navigate('/login') }} style={{
            padding: '6px 14px', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 8,
            background: 'rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer', fontSize: 12,
          }}>退出</button>
        </div>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 16px', maxWidth: 540, margin: '0 auto', width: '100%' }}>
        {loading && <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>加载中...</div>}
        {msg && (
          <div style={{
            padding: '10px 14px', marginBottom: 16, borderRadius: 10,
            background: msg.includes('成功') ? '#f0fdf4' : '#fef2f2',
            border: `1px solid ${msg.includes('成功') ? '#bbf7d0' : '#fecaca'}`,
            color: msg.includes('成功') ? '#16a34a' : '#dc2626', fontSize: 13,
          }}>
            {msg}
          </div>
        )}

        {/* Basic info */}
        <div style={{ background: '#fff', padding: 24, borderRadius: 14, border: '1px solid #c7d2fe', marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#1e293b' }}>基本信息</div>
          <div style={{ display: 'flex', gap: 20, alignItems: 'center', marginBottom: 20 }}>
            <div onClick={() => fileInputRef.current?.click()} style={{
              width: 72, height: 72, borderRadius: 16, border: '2px dashed #c7d2fe',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              overflow: 'hidden', background: avatarUrl ? `url(/api/auth/avatar/${avatarUrl}) center/cover` : '#eef2ff',
              flexShrink: 0,
            }}>
              {!avatarUrl && <span style={{ fontSize: 28, color: '#a5b4fc' }}>+</span>}
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#1e293b' }}>{userInfo?.name || user?.name || '--'}</div>
              <div style={{ fontSize: 13, color: '#94a3b8' }}>@{userInfo?.username || user?.username || '--'} · 医生</div>
            </div>
            <input ref={fileInputRef} type="file" accept="image/*" onChange={handleAvatarUpload} style={{ display: 'none' }} />
          </div>

          <div style={rowStyle}><span style={labelStyle}>姓名</span><span style={{ color: '#1e293b' }}>{userInfo?.name || user?.name || '未填写'}</span></div>
          {!editingUser ? (
            <>
              <div style={rowStyle}><span style={labelStyle}>手机号</span><span style={{ color: '#1e293b' }}>{userForm.phone || '未填写'}</span></div>
              <div style={rowStyle}><span style={labelStyle}>邮箱</span><span style={{ color: '#1e293b' }}>{userForm.email || '未填写'}</span></div>
              <button onClick={() => setEditingUser(true)} style={btnPrimary}>编辑</button>
            </>
          ) : (
            <>
              <label style={labelStyle}>手机号</label>
              <input type="text" value={userForm.phone} onChange={(e) => setUserForm({ ...userForm, phone: e.target.value })} style={fieldStyle} />
              <label style={labelStyle}>邮箱</label>
              <input type="email" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} style={fieldStyle} />
              <div style={{ display: 'flex', gap: 12 }}>
                <button onClick={handleSaveUser} disabled={saving} style={btnSuccess}>{saving ? '保存中...' : '保存'}</button>
                <button onClick={() => setEditingUser(false)} style={btnCancel}>取消</button>
              </div>
            </>
          )}
        </div>

        {/* Professional info */}
        {profile && (
          <div style={{ background: '#fff', padding: 24, borderRadius: 14, border: '1px solid #c7d2fe', marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#1e293b' }}>执业信息</div>
            {!editing ? (
              <>
                <div style={rowStyle}><span style={labelStyle}>科室</span><span style={{ color: '#1e293b' }}>{profile.department || '未填写'}</span></div>
                <div style={rowStyle}><span style={labelStyle}>职称</span><span style={{ color: '#1e293b' }}>{profile.title || '未填写'}</span></div>
                <div style={rowStyle}><span style={labelStyle}>专业方向</span><span style={{ color: '#1e293b' }}>{profile.specialty || '未填写'}</span></div>
                <div style={rowStyle}><span style={labelStyle}>执业证号</span><span style={{ color: '#1e293b' }}>{profile.license_no || '未填写'}</span></div>
                <button onClick={() => setEditing(true)} style={btnPrimary}>编辑</button>
              </>
            ) : (
              <>
                <label style={labelStyle}>科室</label>
                <input type="text" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} placeholder="如：心内科" style={fieldStyle} />
                <label style={labelStyle}>职称</label>
                <select value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} style={fieldStyle}>
                  <option value="">请选择</option>
                  <option value="主任医师">主任医师</option>
                  <option value="副主任医师">副主任医师</option>
                  <option value="主治医师">主治医师</option>
                  <option value="住院医师">住院医师</option>
                </select>
                <label style={labelStyle}>专业方向</label>
                <input type="text" value={form.specialty} onChange={(e) => setForm({ ...form, specialty: e.target.value })} placeholder="如：冠心病介入治疗" style={fieldStyle} />
                <label style={labelStyle}>执业证号</label>
                <input type="text" value={form.license_no} onChange={(e) => setForm({ ...form, license_no: e.target.value })} style={fieldStyle} />
                <div style={{ display: 'flex', gap: 12 }}>
                  <button onClick={handleSaveProfessional} disabled={saving} style={btnSuccess}>{saving ? '保存中...' : '保存'}</button>
                  <button onClick={() => setEditing(false)} style={btnCancel}>取消</button>
                </div>
              </>
            )}
          </div>
        )}

        {/* Password */}
        <div style={{ background: '#fff', padding: 24, borderRadius: 14, border: '1px solid #c7d2fe', marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#1e293b' }}>修改密码</div>
          {!changingPw ? (
            <button onClick={() => setChangingPw(true)} style={btnDanger}>修改密码</button>
          ) : (
            <>
              {pwMsg && <div style={{ padding: '10px 14px', marginBottom: 12, borderRadius: 10, background: pwMsg.includes('成功') ? '#f0fdf4' : '#fef2f2', color: pwMsg.includes('成功') ? '#16a34a' : '#dc2626', fontSize: 13 }}>{pwMsg}</div>}
              <label style={labelStyle}>原密码</label>
              <input type="password" value={pwForm.oldPassword} onChange={(e) => setPwForm({ ...pwForm, oldPassword: e.target.value })} style={fieldStyle} />
              <label style={labelStyle}>新密码</label>
              <input type="password" value={pwForm.newPassword} onChange={(e) => setPwForm({ ...pwForm, newPassword: e.target.value })} style={fieldStyle} />
              <label style={labelStyle}>确认新密码</label>
              <input type="password" value={pwForm.confirmPassword} onChange={(e) => setPwForm({ ...pwForm, confirmPassword: e.target.value })} style={fieldStyle} />
              <div style={{ display: 'flex', gap: 12 }}>
                <button onClick={handleChangePassword} disabled={pwSaving} style={btnDanger}>{pwSaving ? '修改中...' : '确认修改'}</button>
                <button onClick={() => { setChangingPw(false); setPwMsg(''); setPwForm({ oldPassword: '', newPassword: '', confirmPassword: '' }) }} style={btnCancel}>取消</button>
              </div>
            </>
          )}
        </div>

        {/* Delete */}
        <div style={{ background: '#fff', padding: 24, borderRadius: 14, border: '1px solid #c7d2fe', marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#1e293b' }}>注销账号</div>
          {delMsg && <div style={{ padding: '10px 14px', marginBottom: 12, borderRadius: 10, background: '#fef2f2', color: '#dc2626', fontSize: 13 }}>{delMsg}</div>}
          {!showingDelete ? (
            <button onClick={() => setShowingDelete(true)} style={btnDangerOutline}>注销账号</button>
          ) : (
            <>
              <div style={{ fontSize: 13, color: '#dc2626', marginBottom: 12, lineHeight: 1.6 }}>
                注销后所有数据将被永久删除，此操作不可撤销。请输入密码确认：
              </div>
              <label style={labelStyle}>密码</label>
              <input type="password" value={delForm.password} onChange={(e) => setDelForm({ ...delForm, password: e.target.value })} style={fieldStyle} />
              <label style={labelStyle}>再次输入密码</label>
              <input type="password" value={delForm.confirmPassword} onChange={(e) => setDelForm({ ...delForm, confirmPassword: e.target.value })} style={fieldStyle} />
              <div style={{ display: 'flex', gap: 12 }}>
                <button onClick={handleDeleteAccount} disabled={deleting} style={btnDanger}>{deleting ? '注销中...' : '确认注销'}</button>
                <button onClick={() => { setShowingDelete(false); setDelMsg(''); setDelForm({ password: '', confirmPassword: '' }) }} style={btnCancel}>取消</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

const labelStyle: React.CSSProperties = { color: '#94a3b8', fontSize: 13, marginBottom: 4, display: 'block', fontWeight: 500 }
const rowStyle: React.CSSProperties = { padding: '10px 0', borderBottom: '1px solid #f1f5f9', display: 'flex', gap: 24, fontSize: 14 }
const fieldStyle: React.CSSProperties = {
  width: '100%', padding: '10px 14px', border: '1.5px solid #e2e8f0', borderRadius: 10, fontSize: 14, marginBottom: 12,
  background: '#f8fafc', color: '#1e293b',
}
const btnPrimary: React.CSSProperties = { marginTop: 8, padding: '8px 24px', background: ACCENT, color: '#fff', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer' }
const btnSuccess: React.CSSProperties = { padding: '8px 24px', background: '#10b981', color: '#fff', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer' }
const btnCancel: React.CSSProperties = { padding: '8px 24px', background: '#fff', color: '#64748b', border: '1.5px solid #e2e8f0', borderRadius: 8, fontSize: 13, cursor: 'pointer' }
const btnDanger: React.CSSProperties = { padding: '8px 24px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer' }
const btnDangerOutline: React.CSSProperties = { padding: '8px 24px', background: '#fff', color: '#ef4444', border: '1.5px solid #fca5a5', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer' }
