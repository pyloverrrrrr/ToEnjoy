import { create } from 'zustand'
import type { ChatMessage, CitationSource, ReActStep, ReportInterpretation } from '../types'

interface ChatState {
  messages: ChatMessage[]
  isStreaming: boolean
  currentStreaming: string
  currentSources: CitationSource[]
  currentReasoningSteps: ReActStep[]

  addMessage: (msg: ChatMessage) => void
  addReport: (report: ReportInterpretation) => void
  setStreaming: (v: boolean) => void
  appendStreaming: (content: string) => void
  setSources: (sources: CitationSource[]) => void
  setReasoningSteps: (steps: ReActStep[]) => void
  finishStreaming: () => void
  loadMessages: (msgs: ChatMessage[]) => void
  clear: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  currentStreaming: '',
  currentSources: [],
  currentReasoningSteps: [],

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  addReport: (report) =>
    set((s) => ({
      messages: [
        ...s.messages,
        {
          id: `report_${Date.now()}`,
          role: 'assistant',
          content: report.summary,
          reportResult: report,
          timestamp: new Date().toISOString(),
        },
      ],
    })),

  setStreaming: (v) => set({ isStreaming: v }),

  appendStreaming: (content) =>
    set((s) => ({ currentStreaming: s.currentStreaming + content })),

  setSources: (sources) => set({ currentSources: sources }),

  setReasoningSteps: (steps) => set({ currentReasoningSteps: steps }),

  finishStreaming: () =>
    set((s) => {
      const finalMsg: ChatMessage = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: s.currentStreaming,
        sources: s.currentSources,
        reasoningSteps: s.currentReasoningSteps.length > 0 ? [...s.currentReasoningSteps] : undefined,
        timestamp: new Date().toISOString(),
      }
      return {
        messages: [...s.messages, finalMsg],
        isStreaming: false,
        currentStreaming: '',
        currentSources: [],
        currentReasoningSteps: [],
      }
    }),

  loadMessages: (msgs: ChatMessage[]) =>
    set({
      messages: msgs,
      isStreaming: false,
      currentStreaming: '',
      currentSources: [],
      currentReasoningSteps: [],
    }),

  clear: () =>
    set({
      messages: [],
      isStreaming: false,
      currentStreaming: '',
      currentSources: [],
      currentReasoningSteps: [],
    }),
}))
