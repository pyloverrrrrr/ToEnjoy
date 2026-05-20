import { useState } from 'react'
import type { ChatMessage } from '../../types'
import MarkdownRenderer from './MarkdownRenderer'
import CitationCard from './CitationCard'

interface Props {
  message: ChatMessage
  accentColor?: string
}

export default function ChatBubble({ message, accentColor = '#e11d48' }: Props) {
  const isUser = message.role === 'user'
  const [reasoningOpen, setReasoningOpen] = useState(false)
  const hasReasoning = !isUser && message.reasoningSteps && message.reasoningSteps.length > 0

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 16,
      }}
    >
      <div
        style={{
          maxWidth: '75%',
          background: isUser ? accentColor : '#ffffff',
          color: isUser ? '#fff' : '#1e293b',
          borderRadius: 14,
          padding: '12px 16px',
          borderBottomRightRadius: isUser ? 4 : 14,
          borderBottomLeftRadius: isUser ? 14 : 4,
          boxShadow: isUser ? 'none' : '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
          border: isUser ? 'none' : '1px solid #e2e8f0',
        }}
      >
        {isUser ? (
          <span style={{ lineHeight: 1.6, fontSize: 14 }}>{message.content}</span>
        ) : message.reportResult ? (
          <>
            <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14, color: accentColor }}>📋 报告解读</div>
            <div style={{ fontSize: 13, lineHeight: 1.6, color: '#475569' }}>{message.reportResult.summary}</div>
            {message.reportResult.sections.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {message.reportResult.sections.map((s, i) => (
                  <div key={i} style={{ marginBottom: 8 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#64748b' }}>{s.title}</div>
                    <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.5 }}>{s.content}</div>
                  </div>
                ))}
              </div>
            )}
            <div style={{ marginTop: 8, fontSize: 11, color: '#94a3b8', fontStyle: 'italic' }}>{message.reportResult.disclaimer}</div>
          </>
        ) : (
          <>
            {/* Trust badge */}
            {message.sources && message.sources.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <span style={{
                  fontSize: 11,
                  background: '#f0fdf4',
                  color: '#16a34a',
                  padding: '3px 10px',
                  borderRadius: 20,
                  border: '1px solid #bbf7d0',
                  fontWeight: 500,
                }}>
                  基于知识库检索 · {message.sources.length} 篇参考文献
                </span>
              </div>
            )}
            {(!message.sources || message.sources.length === 0) && message.role === 'assistant' && (
              <div style={{ marginBottom: 10 }}>
                <span style={{
                  fontSize: 11,
                  background: '#fffbeb',
                  color: '#d97706',
                  padding: '3px 10px',
                  borderRadius: 20,
                  border: '1px solid #fde68a',
                  fontWeight: 500,
                }}>
                  基于通用医学知识
                </span>
              </div>
            )}

            <MarkdownRenderer content={message.content} />

            {/* Reasoning chain toggle */}
            {hasReasoning && (
              <div style={{ marginTop: 12, borderTop: '1px solid #f1f5f9', paddingTop: 10 }}>
                <button
                  onClick={() => setReasoningOpen(!reasoningOpen)}
                  style={{
                    padding: '4px 12px',
                    border: '1px solid #e2e8f0',
                    borderRadius: 6,
                    background: '#f8fafc',
                    cursor: 'pointer',
                    fontSize: 12,
                    color: '#64748b',
                    fontWeight: 500,
                  }}
                >
                  {reasoningOpen ? '收起推理过程 ▲' : `查看推理过程 (${message.reasoningSteps!.length} 步) ▼`}
                </button>
                {reasoningOpen && (
                  <div style={{ marginTop: 8 }}>
                    {message.reasoningSteps!.map((step, i) => (
                      <div key={i} style={{ marginBottom: 6, fontSize: 12 }}>
                        {step.thought && (
                          <div style={{ background: '#f0f5ff', padding: '6px 10px', borderRadius: 6, marginBottom: 4, color: '#1d39c4' }}>
                            <strong>思考:</strong> {step.thought}
                          </div>
                        )}
                        {step.action && step.action !== 'finish' && (
                          <div style={{ background: '#fffbeb', padding: '6px 10px', borderRadius: 6, marginBottom: 4, color: '#92400e' }}>
                            <strong>行动:</strong> {step.action}
                            {step.action_input && Object.keys(step.action_input).length > 0 && (
                              <span style={{ color: '#94a3b8' }}> ({JSON.stringify(step.action_input)})</span>
                            )}
                          </div>
                        )}
                        {step.observation && (
                          <div style={{ background: '#f5f3ff', padding: '6px 10px', borderRadius: 6, color: '#5b21b6', maxHeight: 100, overflow: 'auto' }}>
                            <strong>观察:</strong> {step.observation.length > 200 ? step.observation.slice(0, 200) + '...' : step.observation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Citation sources */}
            {message.sources && message.sources.length > 0 && (
              <div style={{ marginTop: 12, borderTop: '1px solid #f1f5f9', paddingTop: 10 }}>
                <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 6, fontWeight: 500 }}>引用来源:</div>
                {message.sources.map((s, i) => (
                  <CitationCard key={i} source={s} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
