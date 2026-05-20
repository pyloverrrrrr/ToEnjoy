import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { useSearchStore } from '../../stores/searchStore'
import { search } from '../../api/search'
import SearchPanel from '../../components/doctor/SearchPanel'

export default function DoctorSearch() {
  const [input, setInput] = useState('')
  const [searchTypeFilter, setSearchTypeFilter] = useState('')
  const [patientIdInput, setPatientIdInput] = useState('')
  const [showPatientInput, setShowPatientInput] = useState(false)
  const navigate = useNavigate()

  const token = useAuthStore((s) => s.token)
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const { results, sources, loading, setQuery, setResults, setLoading } = useSearchStore()

  useEffect(() => {
    if (!token) navigate('/login')
  }, [token, navigate])

  const handleSearch = async () => {
    const q = input.trim()
    if (!q || !token) return
    setQuery(q)
    setLoading(true)
    try {
      const data = await search(q, token)
      setResults(data.results, data.sources)
      // Save search query to localStorage history
      try {
        const stored = JSON.parse(localStorage.getItem('remediant_search_history') || '[]')
        stored.unshift({ query: q, resultCount: data.results.length, timestamp: new Date().toISOString() })
        localStorage.setItem('remediant_search_history', JSON.stringify(stored.slice(0, 50)))
      } catch { /* ignore localStorage errors */ }
    } catch (err) {
      console.error('Search error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f8fafc' }}>
      {/* Header */}
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
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#fff' }}>全屏检索</h2>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={() => navigate('/doctor/chat')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}>
            智能问诊
          </button>
          <button onClick={() => navigate('/doctor/patients')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13 }}>
            患者列表
          </button>
          <button onClick={() => navigate('/doctor/search-history')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13 }}>
            检索历史
          </button>
          <button onClick={() => navigate('/doctor/profile')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13 }}>
            个人档案
          </button>
          {!showPatientInput ? (
            <button onClick={() => setShowPatientInput(true)} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer', fontSize: 13 }}>
              患者病历
            </button>
          ) : (
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input
                type="number"
                placeholder="患者ID"
                value={patientIdInput}
                onChange={(e) => setPatientIdInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && patientIdInput.trim()) {
                    navigate(`/doctor/patient/${patientIdInput.trim()}`)
                  }
                }}
                style={{
                  width: 80,
                  padding: '6px 10px',
                  border: '1.5px solid #c7d2fe',
                  borderRadius: 6,
                  fontSize: 13,
                }}
                autoFocus
              />
              <button
                onClick={() => {
                  if (patientIdInput.trim()) {
                    navigate(`/doctor/patient/${patientIdInput.trim()}`)
                  }
                }}
                style={{ padding: '6px 12px', background: '#4f46e5', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 500 }}
              >
                查看
              </button>
              <button onClick={() => { setShowPatientInput(false); setPatientIdInput('') }} style={{ padding: '6px 8px', background: 'transparent', color: 'rgba(255,255,255,0.7)', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
                ✕
              </button>
            </div>
          )}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginLeft: 4 }}>
            {user?.avatar_url && (
              <img
                src={`/api/auth/avatar/${user.avatar_url}`}
                alt="avatar"
                style={{ width: 28, height: 28, borderRadius: 8, objectFit: 'cover', border: '2px solid rgba(255,255,255,0.3)' }}
              />
            )}
            <span style={{ color: 'rgba(255,255,255,0.9)', fontSize: 13, fontWeight: 500 }}>{user?.name} · 医生</span>
          </div>
          <button onClick={() => { logout(); navigate('/login') }} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 8, background: 'rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer', fontSize: 12, backdropFilter: 'blur(4px)' }}>
            退出
          </button>
        </div>
      </header>

      {/* Search input */}
      <div style={{ background: '#fff', padding: '16px 28px', borderBottom: '1px solid #e2e8f0' }}>
        <div style={{ display: 'flex', gap: 12 }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入医学检索关键词，如：二甲双胍肾功能不全剂量调整..."
            style={{
              flex: 1,
              padding: '10px 14px',
              border: '1.5px solid #e2e8f0',
              borderRadius: 10,
              fontSize: 14,
              background: '#f8fafc',
            }}
          />
          <button
            onClick={handleSearch}
            disabled={loading || !input.trim()}
            style={{
              padding: '0 28px',
              background: loading ? '#a5b4fc' : 'linear-gradient(135deg, #4338ca, #6366f1)',
              color: '#fff',
              border: 'none',
              borderRadius: 10,
              fontSize: 15,
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: loading ? 'none' : '0 2px 8px rgba(79,70,229,0.25)',
            }}
          >
            检索
          </button>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
          <select
            value={searchTypeFilter}
            onChange={(e) => setSearchTypeFilter(e.target.value)}
            style={{ padding: '6px 12px', border: '1.5px solid #e2e8f0', borderRadius: 8, fontSize: 13, background: '#f8fafc', color: '#475569' }}
          >
            <option value="">全部类型</option>
            <option value="guideline">临床指南</option>
            <option value="literature">医学文献</option>
            <option value="drug">药品信息</option>
          </select>
        </div>
      </div>

      {/* Results */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <SearchPanel
          results={searchTypeFilter ? results.filter((r) => r.source_type === searchTypeFilter) : results}
          loading={loading}
          hasSearched={sources.length > 0 || results.length > 0}
          filterLabel={searchTypeFilter === 'guideline' ? '临床指南' : searchTypeFilter === 'literature' ? '医学文献' : searchTypeFilter === 'drug' ? '药品信息' : undefined}
        />
      </div>

      {/* Sources summary */}
      {(sources.length > 0 || results.length > 0) && (
        <div style={{ background: '#f8fafc', padding: '12px 28px', borderTop: '1px solid #e2e8f0', fontSize: 12, color: '#64748b' }}>
          共检索到 <strong style={{ color: '#4f46e5' }}>{results.length}</strong> 条结果
          {searchTypeFilter && (() => {
            const filtered = results.filter((r) => r.source_type === searchTypeFilter).length
            return <span>，当前筛选 <b>{searchTypeFilter === 'guideline' ? '临床指南' : searchTypeFilter === 'literature' ? '医学文献' : '药品信息'}</b>：{filtered}/{results.length} 条</span>
          })()}
          ，引用来源 <strong style={{ color: '#4f46e5' }}>{sources.length}</strong> 条
        </div>
      )}
    </div>
  )
}
