import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { useChatStore } from '../../stores/chatStore'
import { useVoiceStore } from '../../stores/voiceStore'
import { streamChat, fetchChatDetail } from '../../api/chat'
import { synthesizeSpeech } from '../../api/voice'
import ChatBubble from '../../components/shared/ChatBubble'
import VoiceInput from '../../components/patient/VoiceInput'
import ReportUploader from '../../components/patient/ReportUploader'
import ReasoningChain from '../../components/shared/ReasoningChain'
import type { ChatMessage } from '../../types'

const ACCENT = '#e11d48'
const ACCENT_GRADIENT = 'linear-gradient(135deg, #be123c, #e11d48)'

export default function PatientChat() {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  const token = useAuthStore((s) => s.token)
  const user = useAuthStore((s) => s.user)
  const sessionId = useAuthStore((s) => s.sessionId)
  const logout = useAuthStore((s) => s.logout)
  const { messages, isStreaming, currentStreaming, currentSources, currentReasoningSteps, addMessage, setStreaming, appendStreaming, setSources, setReasoningSteps, finishStreaming, loadMessages, clear: clearMessages } = useChatStore()
  const { setPlaying, transcript, clearTranscript } = useVoiceStore()
  const [speakingMsgId, setSpeakingMsgId] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const commonQuestions = [
    '我头痛怎么办？',
    '发烧了该吃什么药？',
    '最近失眠怎么改善？',
    '胃不舒服是什么原因？',
    '高血压饮食注意什么？',
    '感冒了需要去医院吗？',
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

  const navBtnStyle = (active?: boolean): React.CSSProperties => ({
    padding: '6px 14px',
    border: active ? 'none' : '1px solid rgba(255,255,255,0.25)',
    borderRadius: 8,
    background: active ? 'rgba(255,255,255,0.2)' : 'transparent',
    color: '#fff',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: active ? 600 : 400,
    backdropFilter: 'blur(4px)',
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#fef2f2' }}>
      {/* Header with gradient */}
      <header style={{
        background: ACCENT_GRADIENT,
        padding: '14px 28px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 12px rgba(225,29,72,0.2)',
      }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
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
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#fff', letterSpacing: '-0.3px' }}>
            患者端
          </h2>
          <span style={{
            fontSize: 11,
            background: 'rgba(255,255,255,0.2)',
            color: '#fff',
            padding: '2px 10px',
            borderRadius: 20,
            fontWeight: 500,
          }}>
            智能问诊
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={() => navigate('/patient/registration')} style={navBtnStyle()}>挂号就诊</button>
          <button onClick={() => navigate('/patient/history')} style={navBtnStyle()}>对话历史</button>
          <button onClick={() => navigate('/patient/medical-record')} style={navBtnStyle()}>我的病历</button>
          <button onClick={() => navigate('/patient/care-plan')} style={navBtnStyle()}>康复计划</button>
          <button onClick={() => navigate('/patient/profile')} style={navBtnStyle()}>个人档案</button>
          <div style={{ width: 1, height: 24, background: 'rgba(255,255,255,0.2)' }} />
          <button
            onClick={() => {
              if (messages.length === 0) return
              if (!window.confirm('确定要清屏吗？')) return
              clearMessages()
            }}
            disabled={messages.length === 0}
            style={{
              ...navBtnStyle(),
              opacity: messages.length === 0 ? 0.4 : 1,
            }}
          >
            清屏
          </button>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginLeft: 4 }}>
            {user?.avatar_url && (
              <img src={`/api/auth/avatar/${user.avatar_url}`} alt="" style={{ width: 30, height: 30, borderRadius: 8, objectFit: 'cover', border: '2px solid rgba(255,255,255,0.3)' }} />
            )}
            <span style={{ color: 'rgba(255,255,255,0.9)', fontSize: 13, fontWeight: 500 }}>{user?.name}</span>
          </div>
          <button onClick={() => { logout(); navigate('/login') }} style={{
            padding: '6px 14px',
            border: '1px solid rgba(255,255,255,0.3)',
            borderRadius: 8,
            background: 'rgba(255,255,255,0.1)',
            color: '#fff',
            cursor: 'pointer',
            fontSize: 12,
            backdropFilter: 'blur(4px)',
          }}>
            退出
          </button>
        </div>
      </header>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 16px' }}>
        {messages.length === 0 && !isStreaming && (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <div style={{
              width: 64,
              height: 64,
              borderRadius: 20,
              background: '#ffe4e6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 28,
              margin: '0 auto 16px',
            }}>
              🩺
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#1e293b', marginBottom: 6 }}>欢迎使用 Remediant 患者助手</div>
            <div style={{ fontSize: 14, color: '#94a3b8' }}>描述您的健康问题，获取智能分析和建议</div>
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
                  border: '1px solid #fecdd3',
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
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: 12, fontSize: 14 }}>正在思考...</div>
        )}
        <ReportUploader />
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{ background: '#fff', padding: '16px 28px', borderTop: '1px solid #fecdd3', boxShadow: '0 -2px 8px rgba(0,0,0,0.04)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
          {commonQuestions.map((q) => (
            <button
              key={q}
              onClick={() => setInput(q)}
              disabled={sending}
              style={{
                padding: '5px 14px',
                border: '1px solid #fecdd3',
                borderRadius: 20,
                background: '#fff1f2',
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
            placeholder="输入您的健康问题..."
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
              background: sending ? '#fda4af' : ACCENT_GRADIENT,
              color: '#fff',
              border: 'none',
              borderRadius: 10,
              fontSize: 15,
              fontWeight: 600,
              cursor: sending ? 'not-allowed' : 'pointer',
              whiteSpace: 'nowrap',
              boxShadow: sending ? 'none' : '0 2px 8px rgba(225,29,72,0.25)',
            }}
          >
            {sending ? '发送中' : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}
