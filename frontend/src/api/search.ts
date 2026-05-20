import type { SearchResult } from '../types'

export async function search(query: string, token: string): Promise<{
  results: SearchResult[]
  sources: Array<{ title: string; type: string; url?: string }>
}> {
  const response = await fetch('/api/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query }),
  })
  if (!response.ok) throw new Error('Search failed')
  return response.json()
}
