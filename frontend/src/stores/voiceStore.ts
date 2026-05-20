import { create } from 'zustand'
import type { RecordingState } from '../types'

interface VoiceState {
  isRecording: boolean
  audioBlob: Blob | null
  transcript: string
  state: RecordingState
  isPlaying: boolean

  startRecording: () => void
  stopRecording: (blob: Blob) => void
  setTranscript: (text: string) => void
  clearTranscript: () => void
  setPlaying: (playing: boolean) => void
  reset: () => void
}

export const useVoiceStore = create<VoiceState>((set) => ({
  isRecording: false,
  audioBlob: null,
  transcript: '',
  state: 'idle',
  isPlaying: false,

  startRecording: () => set({ isRecording: true, state: 'recording', transcript: '' }),
  stopRecording: (blob) => set({ isRecording: false, audioBlob: blob, state: 'transcribing' }),
  setTranscript: (text) => set({ transcript: text, state: 'done' }),
  clearTranscript: () => set({ transcript: '', audioBlob: null, state: 'idle' }),
  setPlaying: (playing) => set({ isPlaying: playing }),
  reset: () => set({
    isRecording: false,
    audioBlob: null,
    transcript: '',
    state: 'idle',
    isPlaying: false,
  }),
}))
