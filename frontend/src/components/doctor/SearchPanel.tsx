import type { SearchResult } from '../../types'

interface Props {
  results: SearchResult[]
  loading: boolean
  hasSearched?: boolean
  filterLabel?: string
  onResultClick?: (result: SearchResult) => void
}

export default function SearchPanel({ results, loading, hasSearched, filterLabel, onResultClick }: Props) {
  if (loading) {
    return <div style={{ padding: 24, textAlign: 'center', color: '#94a3b8' }}>检索中...</div>
  }

  if (results.length === 0) {
    if (!hasSearched) {
      return <div style={{ padding: 24, textAlign: 'center', color: '#94a3b8' }}>请输入检索关键词</div>
    }
    if (filterLabel) {
      return (
        <div style={{ padding: 24, textAlign: 'center', color: '#94a3b8' }}>
          <p style={{ margin: 0, fontSize: 14 }}>当前筛选条件下无匹配结果</p>
          <p style={{ margin: '8px 0 0', fontSize: 12, color: '#cbd5e1' }}>已选类型: {filterLabel}，请切换其他类型或选择"全部类型"</p>
        </div>
      )
    }
    return (
      <div style={{ padding: 24, textAlign: 'center', color: '#94a3b8' }}>
        <p style={{ margin: 0, fontSize: 14 }}>未找到相关结果</p>
        <p style={{ margin: '8px 0 0', fontSize: 12, color: '#cbd5e1' }}>请尝试其他检索关键词</p>
      </div>
    )
  }

  return (
    <div style={{ padding: '8px 0' }}>
      {results.map((r) => (
        <div
          key={r.id}
          onClick={() => onResultClick?.(r)}
          style={{
            padding: '12px 18px',
            borderBottom: '1px solid #f1f5f9',
            cursor: 'pointer',
            transition: 'background 0.2s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = '#f8fafc')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
        >
          <h4 style={{ margin: '0 0 6px 0', fontSize: 14, fontWeight: 600, color: '#4f46e5' }}>{r.title}</h4>
          <p style={{ margin: '0 0 8px 0', fontSize: 13, color: '#64748b', lineHeight: 1.5 }}>
            {r.content.slice(0, 200)}{r.content.length > 200 ? '...' : ''}
          </p>
          <div style={{ fontSize: 11, color: '#94a3b8' }}>
            <span>相关度: {(r.score * 100).toFixed(0)}%</span>
            <span style={{ marginLeft: 12 }}>类型: {r.source_type}</span>
            {r.source.evidence_level && (
              <span style={{ marginLeft: 12 }}>证据等级: {r.source.evidence_level}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
