const TOKEN = () => localStorage.getItem('token') || ''

export async function transcribeAudio(audioBlob: Blob): Promise<{ text: string; duration_ms: number }> {
  const formData = new FormData()
  formData.append('file', audioBlob, 'recording.wav')

  const resp = await fetch('/api/voice/transcribe', {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOKEN()}` },
    body: formData,
  })

  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    throw new Error(`Transcribe failed: ${resp.status}`)
  }

  return resp.json()
}

export async function synthesizeSpeech(text: string, voice = 'zh_female_qingxin', speed = 1.0): Promise<string> {
  const resp = await fetch('/api/voice/synthesize', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN()}`,
    },
    body: JSON.stringify({ text, voice, speed }),
  })

  if (!resp.ok) {
    if (resp.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    throw new Error(`Synthesize failed: ${resp.status}`)
  }

  const data = await resp.json()
  return data.audio_url
}
