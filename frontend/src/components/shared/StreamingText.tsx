import { useEffect, useState } from 'react'

interface Props {
  text: string
  speed?: number
}

export default function StreamingText({ text, speed = 30 }: Props) {
  const [displayed, setDisplayed] = useState('')

  useEffect(() => {
    if (displayed.length >= text.length) return
    const timer = setTimeout(() => {
      setDisplayed(text.slice(0, displayed.length + 3))
    }, speed)
    return () => clearTimeout(timer)
  }, [displayed, text, speed])

  // When text changes externally, reset
  useEffect(() => {
    setDisplayed('')
  }, [])

  return <span style={{ whiteSpace: 'pre-wrap' }}>{displayed}</span>
}
