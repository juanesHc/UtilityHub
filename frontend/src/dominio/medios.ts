export function rutaMedio(nombreArchivo: string): string {
  return `${import.meta.env.BASE_URL}media/${nombreArchivo}`
}

export function prefiereMovimientoReducido(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}
