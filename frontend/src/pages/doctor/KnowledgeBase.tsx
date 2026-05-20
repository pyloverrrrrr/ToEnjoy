import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { uploadDocument, fetchKbDocuments, deleteKbDocument, type KbDocument } from '../../api/kb'

export default function KnowledgeBase() {
  const [collection, setCollection] = useState('kb_professional')
  const [documents, setDocuments] = useState<KbDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [message, setMessage] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  const loadDocuments = useCallback(() => {
    setLoading(true)
    fetchKbDocuments(collection)
      .then(setDocuments)
      .catch(() => setDocuments([]))
      .finally(() => setLoading(false))
  }, [collection])

  useEffect(() => {
    if (!token) { navigate('/login'); return }
    loadDocuments()
  }, [collection, token])

  const handleUpload = async (file: File) => {
    setUploading(true)
    setMessage('')
    try {
      const result = await uploadDocument(file, collection)
      setMessage(`上传成功: ${result.title} (${result.chunks} 个分块)`)
      loadDocuments()
    } catch (err: any) {
      setMessage(`上传失败: ${err.message || '未知错误'}`)
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleUpload(file)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleUpload(file)
  }

  const handleDelete = async (filename: string) => {
    try {
      await deleteKbDocument(filename, collection)
      setMessage(`已删除: ${filename}`)
      loadDocuments()
    } catch (err: any) {
      setMessage(`删除失败: ${err.message || '未知错误'}`)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f8fafc' }}>
      <header style={{
        background: 'linear-gradient(135deg, #4338ca, #6366f1)',
        padding: '14px 28px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 2px 12px rgba(79,70,229,0.2)',
      }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, fontWeight: 700, color: '#fff' }}>R</div>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#fff' }}>知识库管理</h2>
          <button onClick={() => navigate('/doctor/chat')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}>
            智能问诊
          </button>
          <button onClick={() => navigate('/doctor/patients')} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 8, background: 'transparent', color: '#fff', cursor: 'pointer', fontSize: 13 }}>
            患者列表
          </button>
        </div>
        <button onClick={() => { logout(); navigate('/login') }} style={{ padding: '6px 14px', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 8, background: 'rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer', fontSize: 13, backdropFilter: 'blur(4px)' }}>
          退出
        </button>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 16px', maxWidth: 900, margin: '0 auto', width: '100%' }}>
        {/* Controls */}
        <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
          <select value={collection} onChange={(e) => setCollection(e.target.value)} style={{ padding: '8px 14px', border: '1.5px solid #e2e8f0', borderRadius: 10, fontSize: 13, background: '#f8fafc', color: '#475569' }}>
            <option value="kb_professional">专业知识库 (医生)</option>
            <option value="kb_patient">通俗知识库 (患者)</option>
          </select>
        </div>

        {message && (
          <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 10, fontSize: 13, background: message.includes('失败') ? '#fef2f2' : '#f0fdf4', border: `1px solid ${message.includes('失败') ? '#fecaca' : '#bbf7d0'}`, color: message.includes('失败') ? '#dc2626' : '#16a34a' }}>
            {message}
          </div>
        )}

        {/* Upload area */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? '#4f46e5' : '#c7d2fe'}`,
            borderRadius: 14,
            padding: '32px',
            textAlign: 'center',
            background: dragOver ? '#eef2ff' : '#fff',
            cursor: uploading ? 'default' : 'pointer',
            marginBottom: 24,
            pointerEvents: uploading ? 'none' : 'auto',
            transition: 'all 0.2s',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
        >
          <input ref={fileInputRef} type="file" accept=".txt,.pdf,.docx,.md" onChange={handleFileChange} style={{ display: 'none' }} disabled={uploading} />
          <div style={{ fontSize: 40, marginBottom: 8 }}>📄</div>
          <div style={{ fontSize: 14, color: '#64748b', fontWeight: 500 }}>
            {uploading ? '上传解析中...' : '拖拽或点击上传文档 (支持 TXT / PDF / DOCX / MD)'}
          </div>
          <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>最大 50MB · 自动解析分块 · 存入向量数据库</div>
        </div>

        {/* Document list */}
        <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid #f1f5f9', fontWeight: 600, fontSize: 14, color: '#1e293b' }}>
            已索引文档 ({documents.length})
          </div>
          {loading && <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>加载中...</div>}
          {!loading && documents.length === 0 && (
            <div style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>暂无文档，请上传</div>
          )}
          {documents.map((doc) => (
            <div key={doc.filename} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px', borderBottom: '1px solid #f1f5f9' }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, color: '#1e293b', fontWeight: 500 }}>{doc.title}</div>
                <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
                  {doc.filename} · {doc.type} · {doc.chunks} 分块 · {doc.indexed_at ? new Date(doc.indexed_at).toLocaleDateString() : ''}
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc.filename)}
                style={{ padding: '6px 14px', border: '1.5px solid #fca5a5', borderRadius: 6, background: '#fff', cursor: 'pointer', fontSize: 12, color: '#ef4444', fontWeight: 500 }}
              >
                删除
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
