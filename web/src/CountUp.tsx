import { useEffect, useRef, useState } from 'react'

const reduced = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** Número que sube de 0 a `value` cuando entra en pantalla. Con movimiento reducido (o sin soporte) muestra el valor final. */
export function CountUp({ value, format, duration = 1400 }: { value: number; format: (value: number) => string; duration?: number }) {
  const element = useRef<HTMLSpanElement>(null)
  const [shown, setShown] = useState(() => reduced() || !('IntersectionObserver' in window) ? value : 0)

  useEffect(() => {
    if (reduced() || !('IntersectionObserver' in window) || !element.current) { setShown(value); return }
    let frame = 0
    const observer = new IntersectionObserver(entries => {
      if (!entries.some(entry => entry.isIntersecting)) return
      observer.disconnect()
      const started = performance.now()
      const step = (now: number) => {
        const t = Math.min((now - started) / duration, 1)
        setShown(value * (1 - (1 - t) ** 3))
        if (t < 1) frame = requestAnimationFrame(step)
      }
      frame = requestAnimationFrame(step)
    }, { threshold: 0.4 })
    observer.observe(element.current)
    return () => { observer.disconnect(); cancelAnimationFrame(frame) }
  }, [value, duration])

  return <span ref={element}>{format(shown)}</span>
}
