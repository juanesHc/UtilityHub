import type { FiltrosHistorico } from '../../api/tipos'

export const TAMANO_PAGINA_HISTORICO = 10
const PATRON_PERIODO = /^[0-9]{4}-(0[1-9]|1[0-2])$/
const LONGITUD_MAXIMA_APARTAMENTO = 10

export interface FiltrosVisibles {
  torre: string
  servicio: string
  apartamento: string
  periodoDesde: string
  periodoHasta: string
  soloAnomalos: boolean
  pagina: number
}

export type CambiosDeFiltros = Partial<Omit<FiltrosVisibles, 'pagina'>>

const NOMBRE_PARAMETRO: Record<keyof FiltrosVisibles, string> = {
  torre: 'torre',
  servicio: 'servicio',
  apartamento: 'apartamento',
  periodoDesde: 'periodo_desde',
  periodoHasta: 'periodo_hasta',
  soloAnomalos: 'solo_anomalos',
  pagina: 'pagina',
}

function leerPeriodo(valor: string | null): string {
  return valor !== null && PATRON_PERIODO.test(valor) ? valor : ''
}

function leerPagina(valor: string | null): number {
  const pagina = Number(valor)
  return Number.isInteger(pagina) && pagina >= 1 ? pagina : 1
}

export function leerFiltrosDeUrl(parametros: URLSearchParams): FiltrosVisibles {
  return {
    torre: parametros.get(NOMBRE_PARAMETRO.torre) ?? '',
    servicio: (parametros.get(NOMBRE_PARAMETRO.servicio) ?? '').toUpperCase(),
    apartamento: (parametros.get(NOMBRE_PARAMETRO.apartamento) ?? '').slice(0, LONGITUD_MAXIMA_APARTAMENTO),
    periodoDesde: leerPeriodo(parametros.get(NOMBRE_PARAMETRO.periodoDesde)),
    periodoHasta: leerPeriodo(parametros.get(NOMBRE_PARAMETRO.periodoHasta)),
    soloAnomalos: parametros.get(NOMBRE_PARAMETRO.soloAnomalos) === 'true',
    pagina: leerPagina(parametros.get(NOMBRE_PARAMETRO.pagina)),
  }
}

export function escribirFiltrosEnUrl(filtros: FiltrosVisibles): URLSearchParams {
  const parametros = new URLSearchParams()
  const textos: Array<[keyof FiltrosVisibles, string]> = [
    ['torre', filtros.torre],
    ['servicio', filtros.servicio],
    ['apartamento', filtros.apartamento.trim()],
    ['periodoDesde', filtros.periodoDesde],
    ['periodoHasta', filtros.periodoHasta],
  ]
  for (const [nombre, valor] of textos) {
    if (valor !== '') {
      parametros.set(NOMBRE_PARAMETRO[nombre], valor)
    }
  }
  if (filtros.soloAnomalos) {
    parametros.set(NOMBRE_PARAMETRO.soloAnomalos, 'true')
  }
  if (filtros.pagina > 1) {
    parametros.set(NOMBRE_PARAMETRO.pagina, String(filtros.pagina))
  }
  return parametros
}

export function rangoDePeriodosInvertido(filtros: FiltrosVisibles): boolean {
  return filtros.periodoDesde !== '' && filtros.periodoHasta !== '' && filtros.periodoDesde > filtros.periodoHasta
}

export function hayFiltrosActivos(filtros: FiltrosVisibles): boolean {
  return (
    filtros.torre !== '' ||
    filtros.servicio !== '' ||
    filtros.apartamento.trim() !== '' ||
    filtros.periodoDesde !== '' ||
    filtros.periodoHasta !== '' ||
    filtros.soloAnomalos
  )
}

export function convertirEnFiltrosDeApi(filtros: FiltrosVisibles): FiltrosHistorico {
  return {
    torre: filtros.torre || undefined,
    servicio: filtros.servicio || undefined,
    apartamento: filtros.apartamento.trim() || undefined,
    periodo_desde: filtros.periodoDesde || undefined,
    periodo_hasta: filtros.periodoHasta || undefined,
    solo_anomalos: filtros.soloAnomalos || undefined,
    pagina: filtros.pagina,
    tamano_pagina: TAMANO_PAGINA_HISTORICO,
  }
}

export function claveDeConsulta(filtros: FiltrosVisibles): string {
  return escribirFiltrosEnUrl(filtros).toString()
}
