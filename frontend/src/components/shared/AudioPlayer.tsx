import { useEffect, useRef } from 'react'
import { useVoiceStore } from '../../stores/voiceStore'

interface Props {
  audioBlob: Blob | null
}

export default function AudioPlayer({ audioBlob }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const { isPlaying, setPlaying } = useVoiceStore()

  useEffect(() => {
    if (!audioBlob || !audioRef.current) return
    const url = URL.createObjectURL(audioBlob)
    audioRef.current.src = url
    return () => URL.revokeObjectURL(url)
  }, [audioBlob])

  if (!audioBlob) return null

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <audio
        ref={audioRef}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        style={{ display: 'none' }}
      />
      <button
        onClick={() => audioRef.current?.play()}
        disabled={isPlaying}
        style={{
          padding: '4px 12px',
          border: '1px solid #d9d9d9',
          borderRadius: 4,
          background: isPlaying ? '#f5f5f5' : '#fff',
          cursor: isPlaying ? 'not-allowed' : 'pointer',
          fontSize: 13,
        }}
      >
        {isPlaying ? '播放中...' : '🔊 播放语音'}
      </button>
    </div>
  )
}
