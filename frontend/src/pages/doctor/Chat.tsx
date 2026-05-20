import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { useChatStore } from '../../stores/chatStore'
import { useSearchStore } from '../../stores/searchStore'
import { useVoiceStore } from '../../stores/voiceStore'
import { streamChat, fetchChatDetail } from '../../api/chat'
import { search } from '../../api/search'
import { synthesizeSpeech } from '../../api/voice'
import ChatBubble from '../../components/shared/ChatBubble'
import VoiceInput from '../../components/patient/VoiceInput'
import ReasoningChain from '../../components/shared/ReasoningChain'
import SearchPanel from '../../components/doctor/SearchPanel'
import type { ChatMessage, SearchResult } from '../../types'

const ACCENT = '#4f46e5'
const ACCENT_GRADIENT = 'linear-gradient(135deg, #4338ca, #6366f1)'

export default function DoctorChat() {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [searchInput, setSearchInput] = useState('')
  const [searchTypeFilter, setSearchTypeFilter] = useState('')
  const [speakingMsgId, setSpeakingMsgId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const navigate = useNavigate()

  const token = useAuthStore((s) => s.token)
  const user = useAuthStore((s) => s.user)
  const sessionId = useAuthStore((s) => s.sessionId)
  const logout = useAuthStore((s) => s.logout)
  const { messages, isStreaming, currentStreaming, currentSources, currentReasoningSteps, addMessage, setStreaming, appendStreaming, setSources, setReasoningSteps, finishStreaming, loadMessages, clear: clearMessages } = useChatStore()
  const { results, sources, loading, setQuery, setResults, setLoading } = useSearchStore()
  const { setPlaying, transcript, clearTranscript } = useVoiceStore()

  const doctorCommonQuestions = [
    '二甲双胍在CKD 3期患者中如何调整剂量？',
    '高血压合并HFpEF的用药策略？',
    'NCCN 2025 NSCLC免疫治疗最新推荐？',
    '房颤患者抗凝药物的选择与监测？',
    'SGLT2抑制剂在非糖尿病CKD患者中的应用？',
  ]

  useEffect(() => {
    if (!token) navigate('/login')
  }, [token, navigate])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentStreaming])

  useEffect(() => {
    if (transcript) {
      setInput((prev) => prev ? `${prev} ${transcript}` : transcript)
      clearTranscript()
    }
  }, [transcript])

  useEffect(() => {
    if (messages.length === 0 && sessionId && token) {
      fetchChatDetail(token, sessionId)
        .then((data) => {
          if (data.messages.length > 0) {
            loadMessages(data.messages.map((m) => {
              const msg: ChatMessage = {
                id: `hist_${m.id}`,
                role: m.role as 'user' | 'assistant',
                content: m.content,
                timestamp: m.created_at,
              }
              if (m.intent === 'report_interpretation') {
                try {
                  const parsed = JSON.parse(m.content)
                  msg.reportResult = parsed
                  msg.content = parsed.summary || ''
                } catch { /* not valid JSON */ }
              }
              return msg
            }))
          }
        })
        .catch(() => { /* session may not exist yet */ })
    }
  }, [sessionId, token])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || sending || !token) return

    setInput('')
    setSending(true)
    setStreaming(true)

    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    }
    addMessage(userMsg)

    try {
      for await (const chunk of streamChat(text, sessionId, token)) {
        if (chunk.type === 'chunk' && chunk.content) {
          appendStreaming(chunk.content)
        } else if (chunk.type === 'sources' && chunk.sources) {
          setSources(chunk.sources)
        } else if (chunk.type === 'reasoning_steps' && chunk.steps) {
          setReasoningSteps(chunk.steps)
        } else if (chunk.type === 'done') {
          finishStreaming()
        } else if (chunk.type === 'error') {
          throw new Error(chunk.message || 'Unknown error')
        }
      }
    } catch (err) {
      console.error('Chat error:', err)
      finishStreaming()
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSearch = async () => {
    const q = searchInput.trim()
    if (!q || !token) return
    setQuery(q)
    setLoading(true)
    try {
      const data = await search(q, token)
      setResults(data.results, data.sources)
      try {
        const stored = JSON.parse(localStorage.getItem('remediant_search_history') || '[]')
        stored.unshift({ query: q, resultCount: data.results.length, timestamp: new Date().toISOString() })
        localStorage.setItem('remediant_search_history', JSON.stringify(stored.slice(0, 50)))
      } catch { /* ignore */ }
    } catch (err) {
      console.error('Search error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  const stopAudio = () => {
    const audio = audioRef.current
    if (!audio) return
    audio.onended = null
    audio.pause()
    audio.src = ''
    audio.load()
    audioRef.current = null
    setSpeakingMsgId(null)
    setPlaying(false)
  }

  const handleSpeak = async (msgId: string, content: string) => {
    if (speakingMsgId === msgId) { stopAudio(); return }
    if (speakingMsgId) stopAudio()
    setSpeakingMsgId(msgId)
    try {
      const audioUrl = await synthesizeSpeech(content)
      const audio = new Audio(audioUrl)
      audioRef.current = audio
      audio.onended = () => {
        audioRef.current = null
        setSpeakingMsgId(null)
        setPlaying(false)
      }
      setPlaying(true)
      await audio.play()
    } catch {
      audioRef.current = null
      setSpeakingMsgId(null)
    }
  }

  const handleResultClick = (result: SearchResult) => {
    setInput(`请基于以下文献帮我分析：${result.title}`)
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#f8fafc' }}>
      {/* ====== Left Panel: Knowledge Search (40%) ====== */}
      <div style={{
        width: '40%',
        minWidth: 360,
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid #e2e8f0',
        background: '#fff',
      }}>
        {/* Left Header */}
        <div style={{
          background: ACCENT_GRADIENT,
          padding: '14px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 2px 8px rgba(79,70,229,0.2)',
        }}>
          <h3 style={{ margin: 0, fontSize: 15, color: '#fff', fontWeight: 600 }}>📚 知识检索</h3>
          <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.7)', background: 'rgba(255,255,255,0.15)', padding: '2px 10px', borderRadius: 20 }}>{loading ? '检索中...' : results.length > 0 ? `${results.length} 条结果` : '循证医学'}</span>
        </div>

        {/* Search Input */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              placeholder="输入医学检索关键词..."
              style={{
                flex: 1,
                padding: '10px 14px',
                border: '1.5px solid #e2e8f0',
                borderRadius: 10,
                fontSize: 13,
                background: '#f8fafc',
              }}
            />
            <button
              onClick={handleSearch}
              disabled={loading || !searchInput.trim()}
              style={{
                padding: '0 20px',
                background: loading ? '#a5b4fc' : ACCENT_GRADIENT,
                color: '#fff',
                border: 'none',
                borderRadius: 10,
                fontSize: 13,
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              {loading ? '检索中' : '检索'}
            </button>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            <select
              value={searchTypeFilter}
              onChange={(e) => setSearchTypeFilter(e.target.value)}
              style={{ flex: 1, padding: '6px 10px', border: '1.5px solid #e2e8f0', borderRadius: 8, fontSize: 12, background: '#f8fafc', color: '#475569' }}
            >
              <option value="">全部类型</option>
              <option value="guideline">临床指南</option>
              <option value="literature">医学文献</option>
              <option value="drug">药品信息</option>
            </select>
          </div>
        </div>

        {/* Search Results */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <SearchPanel
            results={searchTypeFilter ? results.filter((r) => r.source_type === searchTypeFilter) : results}
            loading={loading}
            hasSearched={sources.length > 0 || results.length > 0}
            filterLabel={searchTypeFilter === 'guideline' ? '临床指南' : searchTypeFilter === 'literature' ? '医学文献' : searchTypeFilter === 'drug' ? '药品信息' : undefined}
            onResultClick={handleResultClick}
          />
        </div>

        {/* Sources summary */}
        {(sources.length > 0 || results.length > 0) && (
          <div style={{ padding: '12px 20px', borderTop: '1px solid #e2e8f0', fontSize: 12, color: '#64748b', background: '#f8fafc' }}>
            共检索到 <strong style={{ color: ACCENT }}>{results.length}</strong> 条结果
            {searchTypeFilter && (() => {
              const filtered = results.filter((r) => r.source_type === searchTypeFilter).length
              return <span>，当前筛选 <b>{searchTypeFilter === 'guideline' ? '临床指南' : searchTypeFilter === 'literature' ? '医学文献' : '药品信息'}</b>：{filtered}/{results.length} 条</span>
            })()}
            ，引用来源 <strong style={{ color: ACCENT }}>{sources.length}</strong> 条
          </div>
        )}

        {results.length === 0 && !loading && sources.length === 0 && (
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: '40px 20px', fontSize: 13 }}>
            输入关键词开始检索医学文献
          </div>
        )}
      </div>

      {/* ====== Right Panel: Chat (60%) ====== */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Right Header */}
        <header style={{
          background: ACCENT_GRADIENT,
          padding: '14px 28px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 2px 8px rgba(79,70,229,0.2)',
        }}>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <div style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: 'rgba(255,255,255,0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 16,
              fontWeight: 700,
              color: '#fff',
            }}>
              R
            </div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#fff' }}>医生工作站</h3>
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.7)', background: 'rgba(255,255,255,0.15)', padding: '2px 12px', borderRadius: 20, fontWeight: 500 }}>
              专业模式
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button onClick={() => navigate('/doctor/patients')} style={{
              padding: '6px 12px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
              background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 12,
            }}>
              患者列表
            </button>
            <button onClick={() => navigate('/doctor/search')} style={{
              padding: '6px 12px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
              background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 12,
            }}>
              全屏检索
            </button>
            <button onClick={() => navigate('/doctor/search-history')} style={{
              padding: '6px 12px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
              background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 12,
            }}>
              检索历史
            </button>
            <button onClick={() => navigate('/doctor/knowledge-base')} style={{
              padding: '6px 12px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
              background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 12,
            }}>
              知识库
            </button>
            <button onClick={() => navigate('/doctor/profile')} style={{
              padding: '6px 12px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
              background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 12,
            }}>
              个人档案
            </button>
            <div style={{ width: 1, height: 24, background: 'rgba(255,255,255,0.2)' }} />
            <button
              onClick={() => {
                if (messages.length === 0) return
                if (!window.confirm('确定要清屏吗？')) return
                clearMessages()
              }}
              disabled={messages.length === 0}
              style={{
                padding: '6px 12px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8,
                background: 'transparent', color: '#fff', cursor: messages.length === 0 ? 'not-allowed' : 'pointer', fontSize: 12,
                opacity: messages.length === 0 ? 0.4 : 1,
              }}
            >
              清屏
            </button>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginLeft: 4 }}>
              {user?.avatar_url && (
                <img src={`/api/auth/avatar/${user.avatar_url}`} alt="" style={{ width: 28, height: 28, borderRadius: 8, objectFit: 'cover', border: '2px solid rgba(255,255,255,0.3)' }} />
              )}
              <span style={{ color: 'rgba(255,255,255,0.9)', fontSize: 13, fontWeight: 500 }}>{user?.name} · 医生</span>
            </div>
            <button onClick={() => { logout(); navigate('/login') }} style={{
              padding: '6px 12px', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 8,
              background: 'rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer', fontSize: 12,
              backdropFilter: 'blur(4px)',
            }}>
              退出
            </button>
          </div>
        </header>

        {/* Chat Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 16px', background: '#f8fafc' }}>
          {messages.length === 0 && !isStreaming && (
            <div style={{ textAlign: 'center', padding: '60px 0' }}>
              <div style={{
                width: 64, height: 64, borderRadius: 20,
                background: '#eef2ff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 28, margin: '0 auto 16px',
              }}>
                🏥
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#1e293b', marginBottom: 6 }}>Remediant 医生工作站</div>
              <div style={{ fontSize: 14, color: '#94a3b8' }}>临床决策支持 · 循证医学检索 · 智能辅助问诊</div>
            </div>
          )}

          {currentReasoningSteps.length > 0 && (
            <ReasoningChain steps={currentReasoningSteps} />
          )}

          {messages.map((msg) => (
            <div key={msg.id}>
              <ChatBubble message={msg} accentColor={ACCENT} />
              {msg.role === 'assistant' && msg.content && (
                <button
                  onClick={() => handleSpeak(msg.id, msg.content)}
                  style={{
                    marginLeft: 48,
                    marginTop: -4,
                    marginBottom: 12,
                    padding: '4px 12px',
                    border: '1px solid #c7d2fe',
                    borderRadius: 6,
                    background: '#fff',
                    cursor: 'pointer',
                    fontSize: 12,
                    color: speakingMsgId === msg.id ? '#ef4444' : ACCENT,
                    fontWeight: 500,
                  }}
                >
                  {speakingMsgId === msg.id ? '⏹ 停止播放' : '🔊 播放语音'}
                </button>
              )}
            </div>
          ))}

          {isStreaming && currentStreaming && (
            <ChatBubble
              message={{
                id: 'streaming',
                role: 'assistant',
                content: currentStreaming,
                sources: currentSources,
                timestamp: new Date().toISOString(),
              }}
              accentColor={ACCENT}
            />
          )}

          {sending && !currentStreaming && (
            <div style={{ textAlign: 'center', color: '#94a3b8', padding: 12, fontSize: 14 }}>正在分析...</div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div style={{ background: '#fff', padding: '16px 28px', borderTop: '1px solid #e2e8f0', boxShadow: '0 -2px 8px rgba(0,0,0,0.04)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
            {doctorCommonQuestions.map((q) => (
              <button
                key={q}
                onClick={() => { setInput(q) }}
                disabled={sending}
                style={{
                  padding: '5px 14px',
                  border: '1px solid #c7d2fe',
                  borderRadius: 20,
                  background: '#eef2ff',
                  color: ACCENT,
                  fontSize: 12,
                  cursor: sending ? 'not-allowed' : 'pointer',
                  whiteSpace: 'nowrap',
                  fontWeight: 500,
                  opacity: sending ? 0.5 : 1,
                }}
              >
                {q}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
            <VoiceInput />
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入临床问题..."
              rows={2}
              disabled={sending}
              style={{
                flex: 1,
                padding: '10px 14px',
                border: '1.5px solid #e2e8f0',
                borderRadius: 10,
                fontSize: 14,
                resize: 'none',
                fontFamily: 'inherit',
                background: '#f8fafc',
                minHeight: 44,
              }}
            />
            <button
              onClick={handleSend}
              disabled={sending || !input.trim()}
              style={{
                padding: '0 28px',
                height: 44,
                background: sending ? '#a5b4fc' : ACCENT_GRADIENT,
                color: '#fff',
                border: 'none',
                borderRadius: 10,
                fontSize: 15,
                fontWeight: 600,
                cursor: sending ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap',
                boxShadow: sending ? 'none' : '0 2px 8px rgba(79,70,229,0.25)',
              }}
            >
              {sending ? '分析中' : '发送'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
