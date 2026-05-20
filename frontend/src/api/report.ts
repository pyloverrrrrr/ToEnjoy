import type { ReportInfo, ReportInterpretation } from '../types'

const TOKEN = () => localStorage.getItem('token') || ''

export async function uploadReport(file: File): Promise<ReportInfo> {
  const formData = new FormData()
  formData.append('file', file)

  const resp = await fetch('/api/report/upload', {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOKEN()}` },
    body: formData,
  })

  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    throw new Error(`Upload failed: ${resp.status}`)
  }

  return resp.json()
}

export async function* interpretReportStream(reportId: string, sessionId?: string | null): AsyncGenerator<Record<string, unknown>> {
  const url = `/api/report/interpret/${encodeURIComponent(reportId)}/stream${sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''}`
  const resp = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })

  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    throw new Error(`Interpret stream failed: ${resp.status}`)
  }

  const reader = resp.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data) {
          yield JSON.parse(data)
        }
      }
    }
  }
}

export async function interpretReport(reportId: string): Promise<ReportInterpretation> {
  const resp = await fetch(`/api/report/interpret/${encodeURIComponent(reportId)}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOKEN()}` },
  })

  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    throw new Error(`Interpret failed: ${resp.status}`)
  }

  return resp.json()
}
