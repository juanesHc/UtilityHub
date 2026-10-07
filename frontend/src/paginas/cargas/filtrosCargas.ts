import type { Carga, EstadoCarga } from '../../api/tipos'

export const ESTADOS_EN_ORDEN: readonly EstadoCarga[] = ['procesada_completa', 'procesada_parcial', 'rechazada', 'reemplazada']

export interface FiltrosCargas {
  torre: string
  estado: EstadoCarga | ''
}

function esEstadoCarga(valor: string): valor is EstadoCarga {
  return (ESTADOS_EN_ORDEN as readonly string[]).includes(valor)
}

export function leerFiltrosCargas(parametros: URLSearchParams): FiltrosCargas {
  const estado = parametros.get('estado') ?? ''
  return {
    torre: parametros.get('torre') ?? '',
    estado: esEstadoCarga(estado) ? estado : '',
  }
}

export function escribirFiltrosCargas(filtros: FiltrosCargas): URLSearchParams {
  const parametros = new URLSearchParams()
  if (filtros.torre !== '') {
    parametros.set('torre', filtros.torre)
  }
  if (filtros.estado !== '') {
    parametros.set('estado', filtros.estado)
  }
  return parametros
}

export function filtrarPorTorre(cargas: Carga[], torre: string): Carga[] {
  return torre === '' ? cargas : cargas.filter((carga) => carga.codigo_torre.toUpperCase() === torre.toUpperCase())
}

export function filtrarCargas(cargas: Carga[], filtros: FiltrosCargas): Carga[] {
  const deLaTorre = filtrarPorTorre(cargas, filtros.torre)
  return filtros.estado === '' ? deLaTorre : deLaTorre.filter((carga) => carga.estado === filtros.estado)
}

export function contarPorEstado(cargas: Carga[]): Record<EstadoCarga, number> {
  const conteo: Record<EstadoCarga, number> = { procesada_completa: 0, procesada_parcial: 0, rechazada: 0, reemplazada: 0 }
  for (const carga of cargas) {
    conteo[carga.estado] += 1
  }
  return conteo
}

export function tieneProblemas(carga: Carga): boolean {
  return carga.estado === 'procesada_parcial' || carga.estado === 'rechazada'
}
