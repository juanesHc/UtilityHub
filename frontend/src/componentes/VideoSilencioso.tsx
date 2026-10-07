import { useEffect, useRef } from 'react'

interface PropiedadesVideoSilencioso {
  fuente: string
  poster?: string
  className?: string
}

export function VideoSilencioso({ fuente, poster, className }: PropiedadesVideoSilencioso) {
  const referencia = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    const video = referencia.current
    if (video === null) {
      return
    }
    video.muted = true
    video.defaultMuted = true
    video.setAttribute('muted', '')
    video.play().catch(() => undefined)
  }, [fuente])

  return (
    <video
      ref={referencia}
      className={className}
      src={fuente}
      poster={poster}
      autoPlay
      muted
      loop
      playsInline
      preload="auto"
      aria-hidden="true"
    />
  )
}
