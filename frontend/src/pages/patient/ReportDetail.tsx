import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { interpretReport } from '../../api/report'
import type { ReportInterpretation } from '../../types'

export default function ReportDetail() {
  const { reportId } = useParams<{ reportId: string }>()
  const [result, setResult] = useState<ReportInterpretation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    if (!reportId) return
    setLoading(true)
    interpretReport(reportId)
      .then(setResult)
      .catch((err) => setError('加载报告失败: ' + (err.message || '未知错误')))
      .finally(() => setLoading(false))
  }, [reportId])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#fef2f2' }}>
      <header
        style={{
          background: 'linear-gradient(135deg, #be123c, #e11d48)',
          padding: '14px 28px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 2px 12px rgba(225,29,72,0.2)',
        }}
      >
        <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#fff' }}>报告解读</h2>
        <button onClick={() => navigate('/patient/chat')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 8, background: 'rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500, backdropFilter: 'blur(4px)' }}>
          返回
        </button>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 16px', maxWidth: 700, margin: '0 auto', width: '100%' }}>
        {loading && <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>加载中...</div>}
        {error && (
          <div style={{ padding: '12px 16px', background: '#fef2f2', borderRadius: 10, border: '1px solid #fecaca', color: '#dc2626', fontSize: 14 }}>{error}</div>
        )}
        {result && (
          <div style={{ background: '#fff', borderRadius: 14, padding: 28, border: '1px solid #fecdd3', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
            <div style={{ fontWeight: 700, fontSize: 17, color: '#e11d48', marginBottom: 16 }}>📋 报告综合解读</div>
            <div style={{ fontSize: 14, lineHeight: 1.8, color: '#334155', marginBottom: 24 }}>{result.summary}</div>

            {result.sections.map((section, i) => (
              <div key={i} style={{ marginBottom: 12, padding: '16px 20px', background: '#fff1f2', borderRadius: 10 }}>
                <div style={{ fontWeight: 600, fontSize: 14, color: '#9f1239', marginBottom: 8 }}>{section.title}</div>
                <div style={{ fontSize: 13, lineHeight: 1.7, color: '#475569' }}>{section.content}</div>
              </div>
            ))}

            <div style={{ fontSize: 12, color: '#94a3b8', fontStyle: 'italic', marginTop: 20, borderTop: '1px solid #fecdd3', paddingTop: 16 }}>{result.disclaimer}</div>
          </div>
        )}
      </div>
    </div>
  )
}
