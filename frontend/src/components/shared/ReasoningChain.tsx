import { useState } from 'react'
import type { ReActStep } from '../../types'

interface Props {
  steps: ReActStep[]
}

const LABELS: Record<string, string> = {
  thought: '思考',
  action: '行动',
  action_input: '行动输入',
  observation: '观察',
}

const COLORS: Record<string, { bg: string; text: string }> = {
  thought: { bg: '#eef2ff', text: '#4f46e5' },
  action: { bg: '#fffbeb', text: '#d97706' },
  action_input: { bg: '#f0fdf4', text: '#16a34a' },
  observation: { bg: '#f5f3ff', text: '#7c3aed' },
}

export default function ReasoningChain({ steps }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (!steps || steps.length === 0) return null

  return (
    <div style={{
      border: '1px solid #e2e8f0',
      borderRadius: 10,
      marginBottom: 12,
      overflow: 'hidden',
      background: '#fff',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: '10px 16px',
          background: '#f8fafc',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 13,
          fontWeight: 600,
          color: '#475569',
          userSelect: 'none',
        }}
      >
        <span>推理链 ({steps.length} 步)</span>
        <span style={{ fontSize: 11, color: '#94a3b8' }}>{expanded ? '收起' : '展开'}</span>
      </div>

      {expanded && (
        <div style={{ padding: '8px 16px 12px' }}>
          {steps.map((step, i) => (
            <div key={i} style={{
              marginBottom: i < steps.length - 1 ? 10 : 0,
              padding: '10px 12px',
              background: '#f8fafc',
              border: '1px solid #f1f5f9',
              borderRadius: 8,
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>
                第 {i + 1} 步
              </div>
              {(['thought', 'action', 'action_input', 'observation'] as const).map((field) => {
                const value = field === 'action_input'
                  ? JSON.stringify(step[field], null, 2)
                  : String(step[field] || '')
                if (!value || value === '{}') return null
                const c = COLORS[field]
                return (
                  <div key={field} style={{ marginBottom: 4 }}>
                    <span style={{
                      display: 'inline-block',
                      background: c.bg,
                      color: c.text,
                      padding: '0 8px',
                      borderRadius: 4,
                      fontSize: 11,
                      fontWeight: 600,
                      marginRight: 6,
                    }}>
                      {LABELS[field]}
                    </span>
                    <span style={{ fontSize: 13, color: '#334155', whiteSpace: 'pre-wrap' }}>
                      {value}
                    </span>
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
