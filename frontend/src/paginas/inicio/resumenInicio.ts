import type { Carga, ClienteApi, CodigoServicio, LecturaHistorico, Servicio } from '../../api/tipos'
import { calcularDesviacionRelativa, calcularRangoConsumoNormal } from '../../dominio/evaluacion'
import {
  formatearConsumo,
  formatearDesviacion,
  formatearPeriodoCorto,
  formatearRango,
  fraseDeCarga,
  presentarEstadoCarga,
} from '../../dominio/formato'

const ANOMALIAS_DESTACADAS = 5
const TAMANO_PAGINA_MAXIMO = 200
const SERVICIOS_EN_ORDEN: readonly CodigoServicio[] = ['AGUA', 'ENERGIA']

export interface AnomaliaDestacada {
  idLectura: number
  nombreTorre: string
  numeroApartamento: string
  codigoServicio: CodigoServicio
  consumoTexto: string
  rangoTexto: string
  desviacionTexto: string
}

export interface ResumenServicio {
  codigoServicio: CodigoServicio
  cantidadAnomalias: number
  hayConsumosPorDebajo: boolean
}

export interface CargaDestacada {
  idCarga: number
  numeroOrden: string
  periodoCorto: string
  nombreTorre: string
  frase: string
  colorFrase: string
  nombreArchivo: string
  filasAceptadas: number
  filasRechazadas: number
  porcentajeAceptadas: string
  porcentajeRechazadas: string
  estadoVisible: string
  colorTinta: string
  colorPunto: string
}

export interface ResumenInicio {
  periodo: string | null
  totalAnomalias: number
  cargasConProblemas: number
  cantidadTorres: number
  anomaliasDestacadas: AnomaliaDestacada[]
  resumenPorServicio: ResumenServicio[]
  cargasDelPeriodo: CargaDestacada[]
}

interface AnomaliaEvaluada {
  lectura: LecturaHistorico
  desviacion: number
  limiteInferior: number
  limiteSuperior: number
}

function periodoMasReciente(periodos: Array<string | undefined>): string | null {
  const presentes = periodos.filter((periodo): periodo is string => periodo !== undefined)
  return presentes.length === 0 ? null : presentes.reduce((mayor, periodo) => (periodo > mayor ? periodo : mayor))
}

async function consultarTodasLasAnomaliasDelPeriodo(cliente: ClienteApi, periodo: string): Promise<LecturaHistorico[]> {
  const anomalias: LecturaHistorico[] = []
  let pagina = 1
  let totalPaginas = 1
  do {
    const resultado = await cliente.consultarHistorico({
      solo_anomalos: true,
      periodo_desde: periodo,
      periodo_hasta: periodo,
      tamano_pagina: TAMANO_PAGINA_MAXIMO,
      pagina,
    })
    anomalias.push(...resultado.lecturas)
    totalPaginas = resultado.total_paginas
    pagina += 1
  } while (pagina <= totalPaginas)
  return anomalias
}

function evaluarAnomalia(lectura: LecturaHistorico, umbralPorServicio: Map<string, number>): AnomaliaEvaluada | null {
  const umbral = umbralPorServicio.get(lectura.codigo_servicio)
  if (lectura.consumo_periodo === null || lectura.promedio_referencia === null || umbral === undefined) {
    return null
  }
  const desviacion = calcularDesviacionRelativa(lectura.consumo_periodo, lectura.promedio_referencia)
  if (desviacion === null) {
    return null
  }
  const rango = calcularRangoConsumoNormal(lectura.promedio_referencia, umbral)
  return { lectura, desviacion, limiteInferior: rango.limiteInferior, limiteSuperior: rango.limiteSuperior }
}

function presentarAnomalia({ lectura, desviacion, limiteInferior, limiteSuperior }: AnomaliaEvaluada): AnomaliaDestacada {
  return {
    idLectura: lectura.id_lectura,
    nombreTorre: lectura.nombre_torre,
    numeroApartamento: lectura.numero_apartamento,
    codigoServicio: lectura.codigo_servicio,
    consumoTexto: formatearConsumo(lectura.consumo_periodo ?? 0, lectura.codigo_servicio),
    rangoTexto: formatearRango(limiteInferior, limiteSuperior, lectura.codigo_servicio),
    desviacionTexto: formatearDesviacion(desviacion),
  }
}

function tieneProblemas(carga: Carga): boolean {
  return carga.estado === 'rechazada' || carga.estado === 'procesada_parcial'
}

function ordenarCargasDelPeriodo(a: Carga, b: Carga): number {
  const prioridad = Number(tieneProblemas(b)) - Number(tieneProblemas(a))
  return prioridad || b.fecha_procesamiento.localeCompare(a.fecha_procesamiento)
}

function porcentaje(parte: number, total: number): string {
  return `${((parte / (total || 1)) * 100).toFixed(1)}%`
}

function presentarCarga(carga: Carga, indice: number): CargaDestacada {
  const presentacion = presentarEstadoCarga(carga.estado)
  const totalFilas = carga.filas_aceptadas + carga.filas_rechazadas
  return {
    idCarga: carga.id_carga,
    numeroOrden: String(indice + 1).padStart(2, '0'),
    periodoCorto: formatearPeriodoCorto(carga.periodo),
    nombreTorre: carga.nombre_torre,
    frase: fraseDeCarga(carga.estado, carga.filas_aceptadas, carga.filas_rechazadas),
    colorFrase: presentacion.colorFrase,
    nombreArchivo: carga.nombre_archivo,
    filasAceptadas: carga.filas_aceptadas,
    filasRechazadas: carga.filas_rechazadas,
    porcentajeAceptadas: porcentaje(carga.filas_aceptadas, totalFilas),
    porcentajeRechazadas: porcentaje(carga.filas_rechazadas, totalFilas),
    estadoVisible: presentacion.nombreVisible,
    colorTinta: presentacion.colorTinta,
    colorPunto: presentacion.colorPunto,
  }
}

function resumirServicios(anomalias: AnomaliaEvaluada[]): ResumenServicio[] {
  return SERVICIOS_EN_ORDEN.map((codigoServicio) => {
    const delServicio = anomalias.filter((anomalia) => anomalia.lectura.codigo_servicio === codigoServicio)
    return {
      codigoServicio,
      cantidadAnomalias: delServicio.length,
      hayConsumosPorDebajo: delServicio.some((anomalia) => anomalia.desviacion < 0),
    }
  })
}

export async function cargarResumenInicio(cliente: ClienteApi): Promise<ResumenInicio> {
  const [lecturaMasReciente, cargas, servicios, torres] = await Promise.all([
    cliente.consultarHistorico({ tamano_pagina: 1 }),
    cliente.listarCargas(),
    cliente.listarServicios(),
    cliente.listarTorres(),
  ])
  const cargasVigentes = cargas.filter((carga) => carga.estado !== 'reemplazada')
  const periodo = periodoMasReciente([
    lecturaMasReciente.lecturas[0]?.periodo,
    periodoMasReciente(cargasVigentes.map((carga) => carga.periodo)) ?? undefined,
  ])
  if (periodo === null) {
    return {
      periodo,
      totalAnomalias: 0,
      cargasConProblemas: 0,
      cantidadTorres: torres.length,
      anomaliasDestacadas: [],
      resumenPorServicio: resumirServicios([]),
      cargasDelPeriodo: [],
    }
  }

  const umbralPorServicio = new Map(servicios.map((servicio: Servicio) => [servicio.codigo, servicio.umbral_desviacion]))
  const anomalias = (await consultarTodasLasAnomaliasDelPeriodo(cliente, periodo))
    .map((lectura) => evaluarAnomalia(lectura, umbralPorServicio))
    .filter((anomalia): anomalia is AnomaliaEvaluada => anomalia !== null)
    .sort((a, b) => Math.abs(b.desviacion) - Math.abs(a.desviacion))
  const cargasDelPeriodo = cargasVigentes.filter((carga) => carga.periodo === periodo).sort(ordenarCargasDelPeriodo)

  return {
    periodo,
    totalAnomalias: anomalias.length,
    cargasConProblemas: cargasDelPeriodo.filter(tieneProblemas).length,
    cantidadTorres: torres.length,
    anomaliasDestacadas: anomalias.slice(0, ANOMALIAS_DESTACADAS).map(presentarAnomalia),
    resumenPorServicio: resumirServicios(anomalias),
    cargasDelPeriodo: cargasDelPeriodo.map(presentarCarga),
  }
}

let resumenPrecargado: { cliente: ClienteApi; promesa: Promise<ResumenInicio> } | null = null

export function precargarResumenInicio(cliente: ClienteApi): void {
  const promesa = cargarResumenInicio(cliente)
  promesa.catch(() => undefined)
  resumenPrecargado = { cliente, promesa }
}

export function tomarResumenPrecargado(cliente: ClienteApi): Promise<ResumenInicio> | null {
  if (resumenPrecargado === null || resumenPrecargado.cliente !== cliente) {
    return null
  }
  const { promesa } = resumenPrecargado
  resumenPrecargado = null
  return promesa
}
