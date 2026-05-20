interface Props {
  lines?: number
}

export default function LoadingSkeleton({ lines = 3 }: Props) {
  return (
    <div style={{ padding: 16 }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 14,
            background: '#f0f0f0',
            borderRadius: 4,
            marginBottom: 8,
            width: `${80 - i * 15}%`,
            animation: 'pulse 1.5s infinite',
          }}
        />
      ))}
    </div>
  )
}
