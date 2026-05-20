import { useState, useCallback, useRef, useEffect } from 'react'
import { uploadReport, interpretReportStream } from '../../api/report'
import { useChatStore } from '../../stores/chatStore'
import { useAuthStore } from '../../stores/authStore'
import type { ReportInterpretation } from '../../types'

type Phase = 'idle' | 'uploading' | 'ocr' | 'llm' | 'done'

const PHASES: { key: Phase; label: string }[] = [
  { key: 'uploading', label: '上传' },
  { key: 'ocr', label: 'OCR识别' },
  { key: 'llm', label: 'AI分析' },
  { key: 'done', label: '完成' },
]

export default function ReportUploader() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')
  const [streamText, setStreamText] = useState('')
  const streamRef = useRef<HTMLPreElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const phaseRef = useRef<Phase>('idle')
  const addReport = useChatStore((s) => s.addReport)
  const sessionId = useAuthStore((s) => s.sessionId)

  const setPhaseAndRef = (p: Phase) => {
    phaseRef.current = p
    setPhase(p)
  }

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight
    }
  }, [streamText])

  const handleFile = useCallback(async (file: File) => {
    setError('')
    setStreamText('')

    try {
      setPhaseAndRef('uploading')
      const uploaded = await uploadReport(file)

      const stream = interpretReportStream(uploaded.report_id, sessionId)
      for await (const event of stream) {
        if (event.type === 'progress') {
          setPhaseAndRef(event.phase as Phase)
        } else if (event.type === 'chunk') {
          setStreamText(prev => prev + (event.content as string || ''))
        } else if (event.type === 'done') {
          const r = event.result as ReportInterpretation
          addReport(r)
          setPhaseAndRef('idle')
        } else if (event.type === 'error') {
          setError(event.message as string || '解读失败')
          setPhaseAndRef('idle')
        }
      }
    } catch {
      if (phaseRef.current !== 'idle') {
        setError('报告上传失败，请检查文件格式')
      }
      setPhaseAndRef('idle')
    }
  }, [sessionId, addReport])

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) {
        handleFile(file)
        e.target.value = ''
      }
    },
    [handleFile],
  )

  const isActive = phase !== 'idle'

  return (
    <div style={{ marginBottom: 12 }}>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        style={{
          border: `2px dashed ${dragOver ? '#1677ff' : '#d9d9d9'}`,
          borderRadius: 8,
          padding: '16px 12px',
          textAlign: 'center',
          background: dragOver ? '#e6f4ff' : '#fafafa',
          transition: 'all 0.2s',
          cursor: isActive ? 'default' : 'pointer',
          pointerEvents: isActive ? 'none' : 'auto',
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/gif,application/pdf"
          onChange={onFileChange}
          style={{ display: 'none' }}
          id="report-upload-input"
          disabled={isActive}
        />
        <label htmlFor="report-upload-input" style={{ cursor: isActive ? 'default' : 'pointer', display: 'block' }}>
          <span style={{ color: '#999', fontSize: 13 }}>
            📄 拖拽或点击上传医学报告 (图片/PDF)
          </span>
        </label>
      </div>

      {/* Phase indicator */}
      {isActive && (
        <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0 }}>
          {PHASES.map((p, i) => {
            const idx = PHASES.findIndex(ph => ph.key === phase)
            let bg = '#e8e8e8'
            let color = '#999'
            if (idx > i) { bg = '#52c41a'; color = '#fff' }
            else if (idx === i) { bg = '#1677ff'; color = '#fff' }

            return (
              <div key={p.key} style={{ display: 'flex', alignItems: 'center' }}>
                {i > 0 && (
                  <div style={{
                    width: 24, height: 2,
                    background: idx > i ? '#52c41a' : '#e8e8e8',
                    margin: '0 4px',
                  }} />
                )}
                <div style={{
                  padding: '3px 10px',
                  borderRadius: 12,
                  background: bg,
                  color,
                  fontSize: 12,
                  fontWeight: idx === i ? 600 : 400,
                  transition: 'all 0.3s',
                }}>
                  {p.label}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Streaming text during LLM phase */}
      {phase === 'llm' && streamText && (
        <div style={{
          marginTop: 8,
          padding: 10,
          background: '#1e1e1e',
          borderRadius: 8,
          maxHeight: 200,
          overflow: 'hidden',
        }}>
          <pre
            ref={streamRef}
            style={{
              margin: 0,
              color: '#d4d4d4',
              fontSize: 12,
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              maxHeight: 180,
              overflow: 'auto',
              fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            }}
          >
            {streamText}
          </pre>
        </div>
      )}

      {error && (
        <div style={{ marginTop: 8, padding: '4px 8px', background: '#fff2f0', borderRadius: 4, color: '#ff4d4f', fontSize: 13 }}>
          {error}
        </div>
      )}
    </div>
  )
}
