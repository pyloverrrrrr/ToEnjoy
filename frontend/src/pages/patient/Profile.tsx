import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { fetchProfile, updateProfile } from '../../api/patient'
import { fetchMe, updateMe, uploadAvatar, changePassword, deleteAccount } from '../../api/auth'
import type { PatientProfileData, UserMeData } from '../../types'

const ACCENT = '#e11d48'
const ACCENT_GRADIENT = 'linear-gradient(135deg, #be123c, #e11d48)'

export default function Profile() {
  const [profile, setProfile] = useState<PatientProfileData | null>(null)
  const [userInfo, setUserInfo] = useState<UserMeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(false)
  const [msg, setMsg] = useState('')

  const [form, setForm] = useState({ gender: '', birthday: '', blood_type: '', allergies: '' })
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
      fetchProfile().catch(() => null),
      fetchMe().catch(() => null),
    ])
      .then(([p, u]) => {
        setProfile(p)
        if (p) setForm({ gender: p.gender || '', birthday: p.birthday || '', blood_type: p.blood_type || '', allergies: p.allergies || '' })
        if (u) {
          setUserInfo(u)
          setUserForm({ phone: u.phone || '', email: u.email || '' })
          if (u.avatar_url || u.name) updateUser({ name: u.name, avatar_url: u.avatar_url })
        }
      })
      .catch(() => setMsg('加载失败'))
      .finally(() => setLoading(false))
  }, [token])

  const handleSaveHealth = async () => {
    setSaving(true); setMsg('')
    try {
      const data: Record<string, string> = {}
      if (form.gender) data.gender = form.gender
      if (form.birthday) data.birthday = form.birthday
      if (form.blood_type) data.blood_type = form.blood_type
      if (form.allergies) data.allergies = form.allergies
      const updated = await updateProfile(data)
      setProfile(updated); setEditing(false); setMsg('健康档案保存成功')
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#fef2f2' }}>
      <header style={{
        background: ACCENT_GRADIENT,
        padding: '14px 28px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 12px rgba(225,29,72,0.2)',
      }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, fontWeight: 700, color: '#fff' }}>R</div>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#fff' }}>个人档案</h2>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={() => navigate('/patient/chat')} style={{
            padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
            background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13,
          }}>返回对话</button>
          <button onClick={() => navigate('/patient/history')} style={{
            padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
            background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13,
          }}>对话历史</button>
          <button onClick={() => navigate('/patient/care-plan')} style={{
            padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
            background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13,
          }}>康复计划</button>
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
        <div style={{ background: '#fff', padding: 24, borderRadius: 14, border: '1px solid #fecdd3', marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#1e293b' }}>基本信息</div>
          <div style={{ display: 'flex', gap: 20, alignItems: 'center', marginBottom: 20 }}>
            <div onClick={() => fileInputRef.current?.click()} style={{
              width: 72, height: 72, borderRadius: 16, border: '2px dashed #fecdd3',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              overflow: 'hidden', background: avatarUrl ? `url(/api/auth/avatar/${avatarUrl}) center/cover` : '#fef2f2',
              flexShrink: 0, transition: 'border-color 0.2s',
            }}>
              {!avatarUrl && <span style={{ fontSize: 28, color: '#fda4af' }}>+</span>}
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#1e293b' }}>{userInfo?.name || user?.name || '--'}</div>
              <div style={{ fontSize: 13, color: '#94a3b8' }}>@{userInfo?.username || user?.username || '--'}</div>
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

        {/* Health profile */}
        {profile && (
          <div style={{ background: '#fff', padding: 24, borderRadius: 14, border: '1px solid #fecdd3', marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#1e293b' }}>健康档案</div>
            {!editing ? (
              <>
                <div style={rowStyle}><span style={labelStyle}>性别</span><span style={{ color: '#1e293b' }}>{profile.gender || '未填写'}</span></div>
                <div style={rowStyle}><span style={labelStyle}>出生日期</span><span style={{ color: '#1e293b' }}>{profile.birthday || '未填写'}</span></div>
                <div style={rowStyle}><span style={labelStyle}>血型</span><span style={{ color: '#1e293b' }}>{profile.blood_type || '未填写'}</span></div>
                <div style={rowStyle}><span style={labelStyle}>过敏史</span><span style={{ color: '#1e293b' }}>{profile.allergies || '未填写'}</span></div>
                <button onClick={() => setEditing(true)} style={btnPrimary}>编辑</button>
              </>
            ) : (
              <>
                <label style={labelStyle}>性别</label>
                <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })} style={fieldStyle}>
                  <option value="">请选择</option>
                  <option value="男">男</option>
                  <option value="女">女</option>
                </select>
                <label style={labelStyle}>出生日期</label>
                <input type="date" value={form.birthday} onChange={(e) => setForm({ ...form, birthday: e.target.value })} style={fieldStyle} />
                <label style={labelStyle}>血型</label>
                <select value={form.blood_type} onChange={(e) => setForm({ ...form, blood_type: e.target.value })} style={fieldStyle}>
                  <option value="">请选择</option>
                  <option value="A">A型</option>
                  <option value="B">B型</option>
                  <option value="AB">AB型</option>
                  <option value="O">O型</option>
                </select>
                <label style={labelStyle}>过敏史</label>
                <input type="text" value={form.allergies} onChange={(e) => setForm({ ...form, allergies: e.target.value })} placeholder="如：青霉素、花粉过敏" style={fieldStyle} />
                <div style={{ display: 'flex', gap: 12 }}>
                  <button onClick={handleSaveHealth} disabled={saving} style={btnSuccess}>{saving ? '保存中...' : '保存'}</button>
                  <button onClick={() => setEditing(false)} style={btnCancel}>取消</button>
                </div>
              </>
            )}
          </div>
        )}

        {/* Password */}
        <div style={{ background: '#fff', padding: 24, borderRadius: 14, border: '1px solid #fecdd3', marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
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
        <div style={{ background: '#fff', padding: 24, borderRadius: 14, border: '1px solid #fecdd3', marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
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
