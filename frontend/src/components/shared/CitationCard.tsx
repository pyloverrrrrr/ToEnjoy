import type { CitationSource } from '../../types'

interface Props {
  source: CitationSource
}

const sourceColors: Record<string, string> = {
  guideline: '#4f46e5',
  literature: '#0891b2',
  drug: '#d97706',
  education: '#7c3aed',
}

export default function CitationCard({ source }: Props) {
  const color = sourceColors[source.type] || '#64748b'

  return (
    <div style={{
      border: `1px solid ${color}22`,
      borderLeft: `3px solid ${color}`,
      borderRadius: 8,
      padding: '8px 12px',
      marginBottom: 6,
      fontSize: 12,
      cursor: source.url ? 'pointer' : 'default',
      color: '#334155',
      background: '#f8fafc',
    }}
      onClick={() => source.url && window.open(source.url, '_blank')}
    >
      <span style={{
        background: color,
        color: '#fff',
        padding: '1px 8px',
        borderRadius: 4,
        marginRight: 8,
        fontSize: 11,
        fontWeight: 600,
      }}>
        {source.type === 'guideline' ? '指南' : source.type === 'literature' ? '文献' : source.type === 'drug' ? '药品' : '科普'}
      </span>
      <strong>{source.title}</strong>
      {source.evidence_level && (
        <span style={{ marginLeft: 8, color: '#94a3b8' }}>证据等级: {source.evidence_level}</span>
      )}
    </div>
  )
}
