import type { Carga, ClienteApi, DetalleLectura, LecturaHistorico } from '../../api/tipos'
import { periodoAnterior, periodosConsecutivosHasta } from '../../dominio/formato'

export const PERIODOS_EN_GRAFICO = 12

export type SituacionEvaluacion =
  | {
      tipo: 'evaluada'
      esAnomalo: boolean
      desviacion: number
      promedio: number
      limiteInferior: number
      limiteSuperior: number
      umbral: number
    }
  | { tipo: 'linea_base' }
  | { tipo: 'hueco'; periodoFaltante: string }
  | { tipo: 'sin_historial' }

export interface PuntoDelHistorial {
  periodo: string
  indice: number
  existeLectura: boolean
  consumo: number | null
  esAnomalo: boolean
  esActual: boolean
  esLineaBase: boolean
}

export interface DetalleCompleto {
  detalle: DetalleLectura
  situacion: SituacionEvaluacion
  puntos: PuntoDelHistorial[]
  carga: Carga | null
}

async function existeLecturaAnterior(cliente: ClienteApi, detalle: DetalleLectura, periodo: string): Promise<boolean> {
  const resultado = await cliente.consultarHistorico({
    torre: detalle.codigo_torre,
    apartamento: detalle.numero_apartamento,
    servicio: detalle.codigo_servicio,
    periodo_hasta: periodoAnterior(periodo),
    tamano_pagina: 1,
  })
  return resultado.total_resultados > 0
}

function determinarSituacion(detalle: DetalleLectura, hayLecturaAnterior: boolean): SituacionEvaluacion {
  if (
    detalle.fue_evaluada &&
    detalle.consumo_periodo !== null &&
    detalle.promedio_referencia !== null &&
    detalle.limite_inferior_normal !== null &&
    detalle.limite_superior_normal !== null &&
    detalle.desviacion_relativa !== null
  ) {
    return {
      tipo: 'evaluada',
      esAnomalo: detalle.es_anomalo,
      desviacion: detalle.desviacion_relativa,
      promedio: detalle.promedio_referencia,
      limiteInferior: detalle.limite_inferior_normal,
      limiteSuperior: detalle.limite_superior_normal,
      umbral: detalle.umbral_desviacion,
    }
  }
  if (detalle.consumo_periodo === null) {
    return hayLecturaAnterior ? { tipo: 'hueco', periodoFaltante: periodoAnterior(detalle.periodo) } : { tipo: 'linea_base' }
  }
  return { tipo: 'sin_historial' }
}

export async function cargarDetalleCompleto(cliente: ClienteApi, idLectura: number): Promise<DetalleCompleto> {
  const detalle = await cliente.obtenerDetalleLectura(idLectura)
  const periodos = periodosConsecutivosHasta(detalle.periodo, PERIODOS_EN_GRAFICO)
  const [historial, cargas] = await Promise.all([
    cliente.consultarHistorico({
      torre: detalle.codigo_torre,
      apartamento: detalle.numero_apartamento,
      servicio: detalle.codigo_servicio,
      periodo_desde: periodos[0],
      periodo_hasta: detalle.periodo,
      tamano_pagina: PERIODOS_EN_GRAFICO,
    }),
    cliente.listarCargas(),
  ])

  const lecturaPorPeriodo = new Map<string, LecturaHistorico>(historial.lecturas.map((lectura) => [lectura.periodo, lectura]))
  const primeraLecturaDelGrafico = periodos.find((periodo) => lecturaPorPeriodo.has(periodo))
  const primeraLectura = primeraLecturaDelGrafico === undefined ? undefined : lecturaPorPeriodo.get(primeraLecturaDelGrafico)

  const [hayLecturaAnteriorAlActual, hayLecturaAnteriorAlGrafico] = await Promise.all([
    detalle.consumo_periodo === null ? existeLecturaAnterior(cliente, detalle, detalle.periodo) : Promise.resolve(true),
    primeraLectura !== undefined && primeraLectura.consumo_periodo === null
      ? existeLecturaAnterior(cliente, detalle, primeraLectura.periodo)
      : Promise.resolve(true),
  ])

  const periodosConDatos = primeraLecturaDelGrafico === undefined ? periodos : periodos.slice(periodos.indexOf(primeraLecturaDelGrafico))
  const puntos = periodosConDatos.map((periodo, indice): PuntoDelHistorial => {
    const lectura = lecturaPorPeriodo.get(periodo)
    const esActual = periodo === detalle.periodo
    return {
      periodo,
      indice,
      existeLectura: lectura !== undefined,
      consumo: esActual ? detalle.consumo_periodo : (lectura?.consumo_periodo ?? null),
      esAnomalo: esActual ? detalle.es_anomalo : (lectura?.es_anomalo ?? false),
      esActual,
      esLineaBase: periodo === primeraLecturaDelGrafico && lectura?.consumo_periodo === null && !hayLecturaAnteriorAlGrafico,
    }
  })

  return {
    detalle,
    situacion: determinarSituacion(detalle, hayLecturaAnteriorAlActual),
    puntos,
    carga: cargas.find((carga) => carga.id_carga === detalle.id_carga) ?? null,
  }
}
