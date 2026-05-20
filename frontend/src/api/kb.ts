const TOKEN = () => localStorage.getItem('token') || ''

export interface KbDocument {
  filename: string
  title: string
  type: string
  chunks: number
  indexed_at: string
}

export interface IndexResult {
  filename: string
  title: string
  type: string
  collection: string
  chunks: number
}

export async function uploadDocument(file: File, collection: string, docType?: string): Promise<IndexResult> {
  const formData = new FormData()
  formData.append('file', file)
  const params = new URLSearchParams({ collection })
  if (docType) params.set('doc_type', docType)
  const resp = await fetch(`/api/kb/documents?${params}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOKEN()}` },
    body: formData,
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    const detail = await resp.json().then(d => d.detail).catch(() => '')
    throw new Error(detail || `Upload failed: ${resp.status}`)
  }
  return resp.json()
}

export async function fetchKbDocuments(collection: string): Promise<KbDocument[]> {
  const resp = await fetch(`/api/kb/documents?collection=${encodeURIComponent(collection)}`, {
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Fetch KB documents failed: ${resp.status}`)
  }
  return resp.json()
}

export async function deleteKbDocument(filename: string, collection: string): Promise<void> {
  const resp = await fetch(`/api/kb/documents/${encodeURIComponent(filename)}?collection=${encodeURIComponent(collection)}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    const detail = await resp.json().then(d => d.detail).catch(() => '')
    throw new Error(detail || `Delete document failed: ${resp.status}`)
  }
}

export async function reindexKb(collection: string): Promise<{ collection: string; indexed: number; results: IndexResult[] }> {
  const resp = await fetch(`/api/kb/reindex?collection=${encodeURIComponent(collection)}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })
  if (!resp.ok) {
    if (resp.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
    throw new Error(`Reindex failed: ${resp.status}`)
  }
  return resp.json()
}
