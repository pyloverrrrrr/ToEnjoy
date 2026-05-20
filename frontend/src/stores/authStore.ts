import { create } from 'zustand'
import type { User } from '../types'
import { useChatStore } from './chatStore'
import { useSearchStore } from './searchStore'

function generateSessionId(): string {
  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function loadUser(): User | null {
  try {
    const raw = localStorage.getItem('user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function loadSessionId(): string {
  return localStorage.getItem('session_id') || ''
}

interface AuthState {
  token: string | null
  user: User | null
  sessionId: string
  setAuth: (token: string, user: User) => void
  updateUser: (data: Partial<User>) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: loadUser(),
  sessionId: loadSessionId(),
  setAuth: (token, user) => {
    const sessionId = generateSessionId()
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
    localStorage.setItem('session_id', sessionId)
    // Clear chat and search state to prevent cross-role data leakage
    useChatStore.getState().clear()
    useSearchStore.getState().clear()
    set({ token, user, sessionId })
  },
  updateUser: (data) => {
    set((state) => {
      const updated = state.user ? { ...state.user, ...data } : null
      if (updated) localStorage.setItem('user', JSON.stringify(updated))
      return { user: updated }
    })
  },
  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('session_id')
    // Clear chat and search state to prevent cross-role data leakage
    useChatStore.getState().clear()
    useSearchStore.getState().clear()
    set({ token: null, user: null, sessionId: '' })
  },
}))
