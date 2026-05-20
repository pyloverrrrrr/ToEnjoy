import type { SSEChunk, ChatHistoryResponse, ChatDetailResponse } from '../types'

export async function* streamChat(
  message: string,
  sessionId: string,
  token: string
): AsyncGenerator<SSEChunk> {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  })

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
      return
    }
    throw new Error(`Chat request failed: ${response.status}`)
  }

  const reader = response.body!.getReader()
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
        try {
          yield JSON.parse(data)
        } catch {
          // skip malformed JSON
        }
      }
    }
  }
}

export async function fetchChatHistory(
  token: string,
  page = 1,
  pageSize = 20
): Promise<ChatHistoryResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  const response = await fetch(`/api/chat/history?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    throw new Error('Failed to fetch history')
  }
  return response.json()
}

export async function fetchChatDetail(
  token: string,
  sessionId: string
): Promise<ChatDetailResponse> {
  const response = await fetch(`/api/chat/history/${encodeURIComponent(sessionId)}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    throw new Error('Failed to fetch chat detail')
  }
  return response.json()
}

export async function deleteSession(token: string, sessionId: string): Promise<void> {
  const response = await fetch(`/api/chat/session/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    throw new Error('Failed to delete session')
  }
}

export async function clearHistory(token: string): Promise<void> {
  const response = await fetch('/api/chat/history', {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    throw new Error('Failed to clear history')
  }
}
