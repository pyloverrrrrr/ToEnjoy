import { useRef, useCallback } from 'react'
import { useVoiceStore } from '../../stores/voiceStore'

const SpeechRecognitionAPI =
  (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

export default function VoiceInput() {
  const recognition = useRef<any>(null)

  const { isRecording, state, startRecording, setTranscript } = useVoiceStore()

  const toggleRecording = useCallback(() => {
    if (recognition.current) {
      recognition.current.stop()
      recognition.current = null
      useVoiceStore.setState({ isRecording: false, state: 'idle' })
      return
    }

    if (!SpeechRecognitionAPI) {
      alert('您的浏览器不支持语音识别，请使用 Chrome 浏览器')
      return
    }

    const rec = new SpeechRecognitionAPI()
    rec.lang = 'zh-CN'
    rec.interimResults = false
    rec.continuous = false

    rec.onresult = (event: any) => {
      const text = event.results[0]?.[0]?.transcript || ''
      if (text) setTranscript(text)
    }

    rec.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error)
      if (event.error === 'not-allowed') {
        alert('请允许浏览器访问麦克风')
      }
      recognition.current = null
      useVoiceStore.setState({ isRecording: false, state: 'idle' })
    }

    rec.onend = () => {
      recognition.current = null
      if (useVoiceStore.getState().state !== 'done') {
        useVoiceStore.setState({ isRecording: false, state: 'idle' })
      } else {
        useVoiceStore.setState({ isRecording: false })
      }
    }

    recognition.current = rec
    rec.start()
    startRecording()
  }, [startRecording, setTranscript])

  const disabled = state === 'transcribing'

  return (
    <button
      onClick={toggleRecording}
      disabled={disabled}
      title={isRecording ? '点击停止录音' : '点击开始语音输入'}
      style={{
        width: 36,
        height: 36,
        borderRadius: '50%',
        border: 'none',
        background: 'transparent',
        cursor: disabled ? 'not-allowed' : 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        opacity: disabled ? 0.4 : 1,
        transition: 'transform 0.15s',
        padding: 0,
      }}
    >
      {isRecording ? (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff4d4f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="1" width="6" height="12" rx="3" fill="#ff4d4f" stroke="none" />
          <path d="M5 11a7 7 0 0 0 14 0" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
      )}
    </button>
  )
}
