import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { uploadAvatar } from '../api/auth'
import axios from 'axios'

const bgGradient = 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)'
const accentGradient = 'linear-gradient(135deg, #e11d48, #f43f5e)'

export default function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('patient')
  const [idNumber, setIdNumber] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('请选择图片文件')
      return
    }
    setAvatarFile(file)
    const reader = new FileReader()
    reader.onload = () => setAvatarPreview(reader.result as string)
    reader.readAsDataURL(file)
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (isRegister) {
        if (password !== password2) {
          setError('两次输入的密码不一致')
          setLoading(false)
          return
        }
        await axios.post('/api/auth/register', { username, password, name, role, id_number: idNumber || null, phone: phone || null })

        const loginRes = await axios.post('/api/auth/login', { username, password })
        setAuth(loginRes.data.token, loginRes.data.user)

        if (avatarFile) {
          try {
            const avatarUrl = await uploadAvatar(avatarFile)
            useAuthStore.getState().updateUser({ avatar_url: avatarUrl })
          } catch { /* avatar upload failed but registration succeeded */ }
        }

        navigate(`/${loginRes.data.user.role}`)
      } else {
        const res = await axios.post('/api/auth/login', { username, password })
        setAuth(res.data.token, res.data.user)
        navigate(`/${res.data.user.role}`)
      }
    } catch (err: any) {
      console.error(isRegister ? '注册失败:' : '登录失败:', err)
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg).join('；'))
      } else if (typeof detail === 'string') {
        setError(detail)
      } else if (err.response) {
        const data = err.response.data
        const msg = typeof data === 'string' ? data : (typeof data === 'object' && data?.message) ? data.message : `服务器错误 (HTTP ${err.response.status})`
        setError(msg)
      } else if (err.request) {
        setError('无法连接服务器，请确认后端服务已启动')
      } else {
        setError(err.message || (isRegister ? '注册失败' : '登录失败'))
      }
    } finally {
      setLoading(false)
    }
  }

  const switchMode = () => {
    setIsRegister(!isRegister)
    setError('')
    setPassword('')
    setPassword2('')
  }

  const inputBase: React.CSSProperties = {
    width: '100%',
    padding: '10px 14px',
    marginBottom: 14,
    border: '1.5px solid #e2e8f0',
    borderRadius: 10,
    fontSize: 14,
    background: '#f8fafc',
    color: '#1e293b',
  }

  const btnPrimary: React.CSSProperties = {
    width: '100%',
    padding: '12px 0',
    background: accentGradient,
    color: '#fff',
    border: 'none',
    borderRadius: 10,
    fontSize: 15,
    fontWeight: 600,
    cursor: loading ? 'not-allowed' : 'pointer',
    opacity: loading ? 0.7 : 1,
    letterSpacing: '0.3px',
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: bgGradient }}>
      {/* Left brand panel */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '0 48px',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Decorative circles */}
        <div style={{ position: 'absolute', top: '-20%', right: '-10%', width: '400px', height: '400px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(225,29,72,0.15) 0%, transparent 70%)' }} />
        <div style={{ position: 'absolute', bottom: '-10%', left: '-5%', width: '300px', height: '300px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)' }} />

        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{
            width: 72,
            height: 72,
            borderRadius: 20,
            background: accentGradient,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 32,
            fontWeight: 800,
            color: '#fff',
            marginBottom: 24,
            boxShadow: '0 8px 32px rgba(225,29,72,0.3)',
          }}>
            R
          </div>
          <h1 style={{ fontSize: 36, fontWeight: 800, color: '#fff', marginBottom: 8, letterSpacing: '-1px' }}>
            Remediant
          </h1>
          <p style={{ fontSize: 15, color: '#94a3b8', lineHeight: 1.6, maxWidth: 360 }}>
            医患双端服务平台
          </p>
          <div style={{ marginTop: 32, display: 'flex', gap: 24 }}>
            <div>
              <div style={{ fontSize: 13, color: '#64748b', marginBottom: 4 }}>患者端</div>
              <div style={{ fontSize: 13, color: '#f43f5e', fontWeight: 600 }}>智能问诊 · 健康管理</div>
            </div>
            <div style={{ width: 1, background: '#334155' }} />
            <div>
              <div style={{ fontSize: 13, color: '#64748b', marginBottom: 4 }}>医生端</div>
              <div style={{ fontSize: 13, color: '#818cf8', fontWeight: 600 }}>临床决策 · 知识检索</div>
            </div>
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div style={{
        width: 460,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '0 48px',
        background: '#fff',
        borderRadius: '32px 0 0 32px',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: accentGradient }} />

        <form onSubmit={handleSubmit}>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>
            {isRegister ? '创建账号' : '欢迎回来'}
          </h2>
          <p style={{ fontSize: 14, color: '#94a3b8', marginBottom: 28 }}>
            {isRegister ? '注册后即可使用全部医疗服务' : '登录以继续使用 Remediant 平台'}
          </p>

          {error && (
            <div style={{
              padding: '10px 14px',
              marginBottom: 16,
              borderRadius: 10,
              background: '#fef2f2',
              border: '1px solid #fecaca',
              color: '#dc2626',
              fontSize: 13,
              lineHeight: 1.5,
            }}>
              {error}
            </div>
          )}

          {isRegister && (
            <div style={{ textAlign: 'center', marginBottom: 16 }}>
              <div
                onClick={() => fileInputRef.current?.click()}
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: '50%',
                  border: '2px dashed #e2e8f0',
                  margin: '0 auto',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                  background: avatarPreview ? `url(${avatarPreview}) center/cover` : '#f1f5f9',
                  transition: 'border-color 0.2s',
                }}
                onMouseEnter={(e) => { if (!avatarPreview) e.currentTarget.style.borderColor = '#e11d48' }}
                onMouseLeave={(e) => { if (!avatarPreview) e.currentTarget.style.borderColor = '#e2e8f0' }}
              >
                {!avatarPreview && <span style={{ fontSize: 22, color: '#cbd5e1' }}>+</span>}
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 6 }}>点击上传头像（选填）</div>
              <input ref={fileInputRef} type="file" accept="image/*" onChange={handleAvatarChange} style={{ display: 'none' }} />
            </div>
          )}

          <input
            type="text"
            placeholder="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={inputBase}
            required
          />
          <input
            type="password"
            placeholder="密码"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={inputBase}
            required
          />
          {isRegister && (
            <>
              <input
                type="password"
                placeholder="确认密码"
                value={password2}
                onChange={(e) => setPassword2(e.target.value)}
                style={inputBase}
                required
              />
              <input
                type="text"
                placeholder="姓名"
                value={name}
                onChange={(e) => setName(e.target.value)}
                style={inputBase}
                required
              />
              <input
                type="text"
                placeholder="手机号（选填）"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                style={inputBase}
              />
              <input
                type="text"
                placeholder="身份证号（选填）"
                value={idNumber}
                onChange={(e) => setIdNumber(e.target.value)}
                style={inputBase}
                maxLength={18}
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                style={{ ...inputBase, background: '#f8fafc' }}
              >
                <option value="patient">患者</option>
                <option value="doctor">医生</option>
              </select>
            </>
          )}
          <button
            type="submit"
            disabled={loading}
            style={btnPrimary}
          >
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                <span style={{ width: 16, height: 16, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block' }} />
                {isRegister ? '注册中...' : '登录中...'}
              </span>
            ) : (isRegister ? '注册' : '登录')}
          </button>

          <div style={{ textAlign: 'center', marginTop: 20 }}>
            <button
              type="button"
              onClick={switchMode}
              style={{
                background: 'none',
                border: 'none',
                color: '#64748b',
                cursor: 'pointer',
                fontSize: 13,
                textDecoration: 'underline',
                textUnderlineOffset: 2,
              }}
            >
              {isRegister ? '已有账号？去登录' : '没有账号？去注册'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
