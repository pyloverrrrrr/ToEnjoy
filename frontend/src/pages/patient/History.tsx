import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { useChatStore } from '../../stores/chatStore'
import { fetchChatHistory, fetchChatDetail, clearHistory } from '../../api/chat'
import type { ChatHistoryItem, ChatDetailMessage } from '../../types'

export default function History() {
  const [items, setItems] = useState<ChatHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatDetailMessage[]>([])
  const [clearing, setClearing] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  const load = async (p: number) => {
    if (!token) return
    setLoading(true)
    try {
      const data = await fetchChatHistory(token, p)
      if (p === 1) {
        setItems(data.items)
      } else {
        setItems((prev) => [...prev, ...data.items])
      }
      setTotal(data.total)
    } catch (err) {
      console.error('Failed to load history', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!token) navigate('/login')
    else load(1)
  }, [token])

  const handleClearAll = async () => {
    if (!window.confirm('确定要清空全部对话历史吗？此操作将同时清除关联的记忆数据，且不可恢复。')) return
    if (!token) return
    setClearing(true)
    try {
      await clearHistory(token)
      useChatStore.getState().clear()
      setItems([])
      setTotal(0)
      setExpanded(null)
      setMessages([])
    } catch (err) {
      console.error('Failed to clear history', err)
    } finally {
      setClearing(false)
    }
  }

  const handleExpand = async (sessionId: string) => {
    if (expanded === sessionId) {
      setExpanded(null)
      setMessages([])
      return
    }
    setExpanded(sessionId)
    setDetailLoading(true)
    try {
      if (!token) return
      const data = await fetchChatDetail(token, sessionId)
      setMessages(data.messages)
    } catch {
      setMessages([])
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#fef2f2' }}>
      <header
        style={{
          background: '#fff1f2',
          padding: '14px 28px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #fecdd3',
        }}
      >
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#e11d48' }}>对话历史</h2>
          <button onClick={() => navigate('/patient/chat')} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#e11d48', fontWeight: 500 }}>
            返回对话
          </button>
          <button onClick={() => navigate('/patient/profile')} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#64748b' }}>
            个人档案
          </button>
          <button onClick={() => navigate('/patient/care-plan')} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#64748b' }}>
            康复计划
          </button>
          <button
            onClick={handleClearAll}
            disabled={clearing || items.length === 0}
            style={{ padding: '6px 14px', border: '1px solid #fca5a5', borderRadius: 8, background: '#fff', cursor: clearing || items.length === 0 ? 'not-allowed' : 'pointer', fontSize: 13, color: '#ef4444', fontWeight: 500 }}
          >
            {clearing ? '清空中...' : '清空历史'}
          </button>
        </div>
        <button onClick={() => { logout(); navigate('/login') }} style={{ padding: '6px 14px', border: '1px solid #fecdd3', borderRadius: 8, background: 'transparent', color: '#64748b', cursor: 'pointer', fontSize: 13 }}>
          退出
        </button>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 16px' }}>
        {loading && items.length === 0 && (
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>加载中...</div>
        )}
        {!loading && items.length === 0 && (
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>暂无对话历史</div>
        )}
        {items.map((item) => (
          <div key={item.session_id} style={{ marginBottom: 8 }}>
            <div
              onClick={() => handleExpand(item.session_id)}
              style={{
                background: expanded === item.session_id ? '#fff1f2' : '#fff',
                padding: '14px 18px',
                borderRadius: 10,
                border: `1px solid ${expanded === item.session_id ? '#e11d48' : '#fecdd3'}`,
                cursor: 'pointer',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              }}
            >
              <div style={{ fontSize: 14, fontWeight: 500, color: '#1e293b', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {item.first_message || '(无内容)'}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#94a3b8' }}>
                <span>{item.message_count} 条消息</span>
                <span>{new Date(item.last_message_at).toLocaleString()}</span>
              </div>
            </div>
            {expanded === item.session_id && (
              <div style={{ background: '#fff', padding: '14px 18px', borderRadius: '0 0 10px 10px', border: '1px solid #e11d48', borderTop: 'none', marginTop: -1 }}>
                {detailLoading ? (
                  <div style={{ textAlign: 'center', color: '#94a3b8', padding: 12 }}>加载中...</div>
                ) : messages.length === 0 ? (
                  <div style={{ textAlign: 'center', color: '#94a3b8', padding: 12 }}>暂无消息</div>
                ) : (
                  messages.map((m) => (
                    <div key={m.id} style={{ marginBottom: 10, padding: '10px 14px', background: m.role === 'user' ? '#fff1f2' : '#f8fafc', borderRadius: 8, fontSize: 13, border: '1px solid #f1f5f9' }}>
                      <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 4 }}>
                        {m.role === 'user' ? '用户' : '助手'} · {new Date(m.created_at).toLocaleString()}
                        {m.intent && <span style={{ marginLeft: 8 }}>意图: {m.intent}</span>}
                      </div>
                      <div style={{ lineHeight: 1.6, whiteSpace: 'pre-wrap', color: '#334155' }}>{m.content}</div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        ))}
        {items.length < total && (
          <button
            onClick={() => { const np = page + 1; setPage(np); load(np) }}
            disabled={loading}
            style={{
              width: '100%',
              padding: '10px',
              border: '1px solid #fecdd3',
              borderRadius: 8,
              background: '#fff',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: 13,
              color: '#e11d48',
              fontWeight: 500,
            }}
          >
            {loading ? '加载中...' : '加载更多'}
          </button>
        )}
      </div>
    </div>
  )
}
