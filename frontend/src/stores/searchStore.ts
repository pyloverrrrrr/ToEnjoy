import { create } from 'zustand'
import type { SearchResult } from '../types'

interface SearchState {
  query: string
  results: SearchResult[]
  sources: Array<{ title: string; type: string; url?: string }>
  loading: boolean
  filters: { source_type?: string; evidence_level?: string; year?: number }

  setQuery: (q: string) => void
  setResults: (results: SearchResult[], sources: Array<{ title: string; type: string; url?: string }>) => void
  setLoading: (v: boolean) => void
  setFilters: (f: Partial<SearchState['filters']>) => void
  clear: () => void
}

export const useSearchStore = create<SearchState>((set) => ({
  query: '',
  results: [],
  sources: [],
  loading: false,
  filters: {},

  setQuery: (query) => set({ query }),
  setResults: (results, sources) => set({ results, sources }),
  setLoading: (loading) => set({ loading }),
  setFilters: (f) => set((s) => ({ filters: { ...s.filters, ...f } })),
  clear: () => set({ query: '', results: [], sources: [], loading: false }),
}))
