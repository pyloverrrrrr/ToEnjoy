import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { fetchChatHistory, clearHistory } from '../../api/chat'
import type { ChatHistoryItem } from '../../types'

interface SearchRecord {
  query: string
  resultCount: number
  timestamp: string
}

export default function SearchHistory() {
  const [chatItems, setChatItems] = useState<ChatHistoryItem[]>([])
  const [searchItems, setSearchItems] = useState<SearchRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [chatTotal, setChatTotal] = useState(0)
  const [clearing, setClearing] = useState(false)
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    if (!token) { navigate('/login'); return }

    // Load chat history from API
    setLoading(true)
    fetchChatHistory(token!, 1)
      .then((data) => {
        setChatItems(data.items)
        setChatTotal(data.total)
      })
      .catch((err) => console.error('Failed to load chat history', err))
      .finally(() => setLoading(false))

    // Load search history from localStorage
    try {
      const stored = JSON.parse(localStorage.getItem('remediant_search_history') || '[]')
      setSearchItems(stored)
    } catch { /* ignore */ }
  }, [token])

  const loadMore = async () => {
    const np = page + 1
    setPage(np)
    try {
      const data = await fetchChatHistory(token!, np)
      setChatItems((prev) => [...prev, ...data.items])
    } catch (err) {
      console.error('Failed to load more', err)
    }
  }

  const handleClearChatHistory = async () => {
    if (!window.confirm('确定要清空全部对话历史吗？此操作将同时清除关联的记忆数据，且不可恢复。')) return
    if (!token) return
    setClearing(true)
    try {
      await clearHistory(token)
      setChatItems([])
      setChatTotal(0)
    } catch (err) {
      console.error('Failed to clear chat history', err)
    } finally {
      setClearing(false)
    }
  }

  const clearSearchHistory = () => {
    localStorage.removeItem('remediant_search_history')
    setSearchItems([])
  }

  const hasChat = chatItems.length > 0
  const hasSearch = searchItems.length > 0
  const isEmpty = !loading && !hasChat && !hasSearch

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f8fafc' }}>
      <header
        style={{
          background: 'linear-gradient(135deg, #4338ca, #6366f1)',
          padding: '14px 28px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 2px 12px rgba(79,70,229,0.2)',
        }}
      >
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, fontWeight: 700, color: '#fff' }}>R</div>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#fff' }}>检索历史</h2>
          <button onClick={() => navigate('/doctor/chat')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}>
            智能问诊
          </button>
          <button onClick={() => navigate('/doctor/search')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13 }}>
            全屏检索
          </button>
          <button onClick={() => navigate('/doctor/patients')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13 }}>
            患者列表
          </button>
        </div>
        <button onClick={() => { logout(); navigate('/login') }} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 8, background: 'rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer', fontSize: 13, backdropFilter: 'blur(4px)' }}>
          退出
        </button>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 16px', maxWidth: 700, margin: '0 auto', width: '100%' }}>
        {loading && (
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>加载中...</div>
        )}
        {isEmpty && (
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>暂无检索历史</div>
        )}

        {/* Search history from localStorage */}
        {hasSearch && (
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h3 style={{ margin: 0, fontSize: 14, color: '#4f46e5' }}>📖 知识库检索记录</h3>
              <button onClick={clearSearchHistory} style={{ padding: '4px 12px', border: '1px solid #c7d2fe', borderRadius: 6, background: '#fff', cursor: 'pointer', fontSize: 11, color: '#64748b' }}>
                清空
              </button>
            </div>
            {searchItems.map((item, i) => (
              <div
                key={`search-${i}-${item.timestamp}`}
                onClick={() => navigate('/doctor/search')}
                style={{
                  background: '#fff',
                  padding: '12px 18px',
                  borderRadius: 10,
                  marginBottom: 6,
                  border: '1px solid #e2e8f0',
                  cursor: 'pointer',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                }}
              >
                <div style={{ fontSize: 14, fontWeight: 500, color: '#1e293b', marginBottom: 4 }}>{item.query}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#94a3b8' }}>
                  <span>{item.resultCount} 条结果</span>
                  <span>{new Date(item.timestamp).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Chat history from API */}
        {hasChat && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h3 style={{ margin: 0, fontSize: 14, color: '#4f46e5' }}>💬 对话记录</h3>
              <button
                onClick={handleClearChatHistory}
                disabled={clearing || chatItems.length === 0}
                style={{ padding: '4px 12px', border: '1px solid #fca5a5', borderRadius: 6, background: '#fff', cursor: clearing || chatItems.length === 0 ? 'not-allowed' : 'pointer', fontSize: 11, color: '#ef4444', fontWeight: 500 }}
              >
                {clearing ? '清空中...' : '清空对话历史'}
              </button>
            </div>
            {chatItems.map((item) => (
              <div
                key={item.session_id}
                style={{
                  background: '#fff',
                  padding: '14px 18px',
                  borderRadius: 10,
                  marginBottom: 8,
                  border: '1px solid #e2e8f0',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
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
            ))}
            {chatItems.length < chatTotal && (
              <button
                onClick={loadMore}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '10px',
                  border: '1px solid #c7d2fe',
                  borderRadius: 8,
                  background: '#fff',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontSize: 13,
                  color: '#4f46e5',
                  fontWeight: 500,
                }}
              >
                {loading ? '加载中...' : '加载更多'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
