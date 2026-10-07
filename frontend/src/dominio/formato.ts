import type { CodigoServicio, EstadoCarga } from '../api/tipos'

const NOMBRES_DE_MES: readonly string[] = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
]

const NUMEROS_EN_PALABRAS: readonly string[] = [
  'cero',
  'una',
  'dos',
  'tres',
  'cuatro',
  'cinco',
  'seis',
  'siete',
  'ocho',
  'nueve',
  'diez',
  'once',
  'doce',
]

const SIGNO_MENOS = '−'
const ESPACIO_SIN_SALTO = ' '

export interface PresentacionServicio {
  nombreVisible: string
  variableColor: string
  unidadVisible: string
  decimales: number
}

const PRESENTACION_POR_SERVICIO: Record<CodigoServicio, PresentacionServicio> = {
  AGUA: { nombreVisible: 'Agua', variableColor: 'var(--agua)', unidadVisible: 'm³', decimales: 1 },
  ENERGIA: { nombreVisible: 'Luz', variableColor: 'var(--luz)', unidadVisible: 'kWh', decimales: 0 },
}

export function presentarServicio(codigoServicio: CodigoServicio): PresentacionServicio {
  return PRESENTACION_POR_SERVICIO[codigoServicio]
}

export function formatearNumero(valor: number, decimales: number): string {
  return new Intl.NumberFormat('es-CO', {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(valor)
}

export function formatearConsumo(valor: number, codigoServicio: CodigoServicio): string {
  const presentacion = presentarServicio(codigoServicio)
  return `${formatearNumero(valor, presentacion.decimales)}${ESPACIO_SIN_SALTO}${presentacion.unidadVisible}`
}

export function formatearLecturaMedidor(valor: number, codigoServicio: CodigoServicio): string {
  return formatearNumero(valor, presentarServicio(codigoServicio).decimales)
}

export function formatearPromedio(valor: number, codigoServicio: CodigoServicio): string {
  const presentacion = presentarServicio(codigoServicio)
  const decimalesMinimos = presentacion.decimales
  const texto = new Intl.NumberFormat('es-CO', {
    minimumFractionDigits: decimalesMinimos,
    maximumFractionDigits: decimalesMinimos === 0 ? 0 : 2,
  }).format(valor)
  return `${texto}${ESPACIO_SIN_SALTO}${presentacion.unidadVisible}`
}

export function nombreCortoDeTorre(nombreTorre: string): string {
  return nombreTorre.replace(/^torre\s+/i, '')
}

export function formatearRango(limiteInferior: number, limiteSuperior: number, codigoServicio: CodigoServicio): string {
  const presentacion = presentarServicio(codigoServicio)
  const inferior = formatearNumero(limiteInferior, presentacion.decimales)
  const superior = formatearNumero(limiteSuperior, presentacion.decimales)
  return `${inferior} – ${superior}${ESPACIO_SIN_SALTO}${presentacion.unidadVisible}`
}

export function formatearDesviacion(desviacionRelativa: number): string {
  const porcentaje = Math.round(Math.abs(desviacionRelativa) * 100)
  const signo = desviacionRelativa < 0 && porcentaje > 0 ? SIGNO_MENOS : '+'
  return `${signo}${porcentaje}${ESPACIO_SIN_SALTO}%`
}

function partesDePeriodo(periodo: string): { anio: string; indiceMes: number } {
  const [anio = '', mes = '1'] = periodo.split('-')
  return { anio, indiceMes: Math.min(11, Math.max(0, Number(mes) - 1)) }
}

function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

export function nombreDelMes(periodo: string): string {
  return NOMBRES_DE_MES[partesDePeriodo(periodo).indiceMes] ?? ''
}

export function formatearPeriodoLargo(periodo: string): string {
  const { anio } = partesDePeriodo(periodo)
  return `${capitalizar(nombreDelMes(periodo))} ${anio}`
}

export function formatearPeriodoCorto(periodo: string): string {
  const { anio } = partesDePeriodo(periodo)
  return `${capitalizar(nombreDelMes(periodo).slice(0, 3))} ${anio}`
}

export function numeroEnPalabras(numero: number): string {
  return NUMEROS_EN_PALABRAS[numero] ?? String(numero)
}

export function pluralizar(cantidad: number, singular: string, plural: string): string {
  return cantidad === 1 ? singular : plural
}

export function iniciales(nombreUsuario: string): string {
  const partes = nombreUsuario.split(/[._\-\s]+/).filter((parte) => parte !== '')
  if (partes.length >= 2) {
    return `${partes[0]?.[0] ?? ''}${partes[1]?.[0] ?? ''}`.toUpperCase()
  }
  return nombreUsuario.slice(0, 2).toUpperCase()
}

export interface PresentacionEstadoCarga {
  nombreVisible: string
  colorTinta: string
  colorPunto: string
  colorFrase: string
}

const PRESENTACION_POR_ESTADO: Record<EstadoCarga, PresentacionEstadoCarga> = {
  procesada_completa: { nombreVisible: 'Completa', colorTinta: '#9FE3BC', colorPunto: 'var(--ok)', colorFrase: '#8A9196' },
  procesada_parcial: { nombreVisible: 'Parcial', colorTinta: '#F8D48A', colorPunto: 'var(--luz)', colorFrase: 'var(--text)' },
  rechazada: { nombreVisible: 'Rechazada', colorTinta: '#FFB4A1', colorPunto: 'var(--anomalia)', colorFrase: '#FFB4A1' },
  reemplazada: { nombreVisible: 'Reemplazada', colorTinta: 'var(--text-3)', colorPunto: 'var(--text-3)', colorFrase: 'var(--text-3)' },
}

export function presentarEstadoCarga(estado: EstadoCarga): PresentacionEstadoCarga {
  return PRESENTACION_POR_ESTADO[estado]
}

export function fraseDeCarga(estado: EstadoCarga, filasAceptadas: number, filasRechazadas: number): string {
  switch (estado) {
    case 'procesada_completa':
      return `Todo en orden, ${filasAceptadas} de ${filasAceptadas}.`
    case 'procesada_parcial':
      return `${capitalizar(numeroEnPalabras(filasRechazadas))} ${pluralizar(
        filasRechazadas,
        'fila no pasó',
        'filas no pasaron',
      )} la validación.`
    case 'rechazada':
      return 'El archivo completo fue rechazado.'
    case 'reemplazada':
      return 'Reemplazada por un archivo más reciente.'
  }
}

export function formatearFechaDeLectura(fechaIso: string): string {
  const [anio = '', mes = '', dia = ''] = fechaIso.slice(0, 10).split('-')
  return `${dia}/${mes}/${anio}`
}

export function formatearFechaDeProcesamiento(fechaHoraUtc: string): string {
  const fecha = interpretarFechaUtc(fechaHoraUtc)
  if (fecha === null) {
    return fechaHoraUtc
  }
  return new Intl.DateTimeFormat('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(fecha)
}

export function periodoAnterior(periodo: string): string {
  const [anio = 0, mes = 1] = periodo.split('-').map(Number)
  return mes === 1 ? `${anio - 1}-12` : `${anio}-${String(mes - 1).padStart(2, '0')}`
}

export function periodosConsecutivosHasta(periodoFinal: string, cantidad: number): string[] {
  const periodos = [periodoFinal]
  while (periodos.length < cantidad) {
    periodos.unshift(periodoAnterior(periodos[0] ?? periodoFinal))
  }
  return periodos
}

export function formatearFechaHora(fechaHoraUtc: string): string {
  const fecha = interpretarFechaUtc(fechaHoraUtc)
  if (fecha === null) {
    return fechaHoraUtc
  }
  const dia = new Intl.DateTimeFormat('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(fecha)
  const hora = new Intl.DateTimeFormat('es-CO', { hour: '2-digit', minute: '2-digit', hour12: false }).format(fecha)
  return `${dia} · ${hora}`
}

function interpretarFechaUtc(fechaHoraUtc: string): Date | null {
  const conZona = /[zZ]|[+-]\d{2}:?\d{2}$/.test(fechaHoraUtc) ? fechaHoraUtc : `${fechaHoraUtc}Z`
  const fecha = new Date(conZona)
  return Number.isNaN(fecha.getTime()) ? null : fecha
}
