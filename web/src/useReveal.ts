import { useEffect } from 'react'
import type { DependencyList } from 'react'

/**
 * Aparece cada `.reveal` al llegar a la pantalla. Sin soporte o con movimiento reducido, todo se ve desde el principio.
 * `deps`: vuelve a buscar elementos `.reveal` cuando cambian (p. ej. tarjetas que se dibujan después de cargar datos).
 */
export function useReveal(deps: DependencyList = []) {
  useEffect(() => {
    const items = document.querySelectorAll<HTMLElement>('.reveal:not(.in)')
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      items.forEach(item => item.classList.add('in'))
      return
    }
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) { entry.target.classList.add('in'); observer.unobserve(entry.target) }
    }, { threshold: 0.12 })
    items.forEach(item => observer.observe(item))
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

/** Los enlaces con ancla (`/#predicciones`) llevan a su sección aunque la página se dibuje después de cargar. */
export function useScrollToHash() {
  useEffect(() => {
    const id = decodeURIComponent(window.location.hash.slice(1))
    if (id) document.getElementById(id)?.scrollIntoView()
  }, [])
}
