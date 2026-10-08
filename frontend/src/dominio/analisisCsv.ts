export const COLUMNAS_ESPERADAS: readonly string[] = [
  'torre',
  'apartamento',
  'servicio',
  'periodo',
  'lectura_acumulada',
  'fecha_lectura',
]
export const TAMANO_MAXIMO_BYTES = 5 * 1024 * 1024
export const FILAS_DE_MUESTRA = 8

const PATRON_NOMBRE_ARCHIVO = /^lecturas_(t\d+)_(\d{4}-(0[1-9]|1[0-2]))\.csv$/i

export interface IdentificacionArchivo {
  codigoTorre: string
  periodo: string
}

export interface FilaCsv {
  numeroLinea: number
  celdas: string[]
}

export type ContenidoCsv =
  | { tipo: 'legible'; encabezado: FilaCsv; filas: FilaCsv[] }
  | { tipo: 'vacio' }
  | { tipo: 'codificacion_invalida' }

export interface AnalisisCsv {
  identificacion: IdentificacionArchivo | null
  encabezado: string[]
  filasMuestra: string[][]
  totalFilas: number
  problemas: string[]
  avisos: string[]
}

export function interpretarNombreArchivo(nombreArchivo: string): IdentificacionArchivo | null {
  const coincidencia = PATRON_NOMBRE_ARCHIVO.exec(nombreArchivo)
  if (coincidencia === null || coincidencia[1] === undefined || coincidencia[2] === undefined) {
    return null
  }
  return { codigoTorre: coincidencia[1].toUpperCase(), periodo: coincidencia[2] }
}

export function separarFilasCsv(texto: string): FilaCsv[] {
  const filas: FilaCsv[] = []
  let celdas: string[] = []
  let celda = ''
  let entreComillas = false
  let lineasLeidas = 0
  for (let indice = 0; indice < texto.length; indice += 1) {
    const caracter = texto.charAt(indice)
    const esFinDeLinea = caracter === '\n' || caracter === '\r'
    if (esFinDeLinea) {
      if (caracter === '\r' && texto.charAt(indice + 1) === '\n') {
        indice += 1
      }
      lineasLeidas += 1
    }
    if (entreComillas) {
      if (esFinDeLinea) {
        celda += '\n'
      } else if (caracter !== '"') {
        celda += caracter
      } else if (texto.charAt(indice + 1) === '"') {
        celda += '"'
        indice += 1
      } else {
        entreComillas = false
      }
    } else if (caracter === '"') {
      entreComillas = true
    } else if (caracter === ',') {
      celdas.push(celda)
      celda = ''
    } else if (esFinDeLinea) {
      celdas.push(celda)
      filas.push({ numeroLinea: lineasLeidas, celdas })
      celdas = []
      celda = ''
    } else {
      celda += caracter
    }
  }
  if (celda !== '' || celdas.length > 0) {
    celdas.push(celda)
    filas.push({ numeroLinea: lineasLeidas + 1, celdas })
  }
  return filas
}

export function leerContenidoCsv(contenido: ArrayBuffer): ContenidoCsv {
  let texto: string
  try {
    texto = new TextDecoder('utf-8', { fatal: true }).decode(contenido)
  } catch {
    return { tipo: 'codificacion_invalida' }
  }
  const filas = separarFilasCsv(texto)
    .map((fila) => ({ numeroLinea: fila.numeroLinea, celdas: fila.celdas.map((celda) => celda.trim()) }))
    .filter((fila) => fila.celdas.some((celda) => celda !== ''))
  const [encabezado, ...filasDeDatos] = filas
  return encabezado === undefined ? { tipo: 'vacio' } : { tipo: 'legible', encabezado, filas: filasDeDatos }
}

function describirDiferenciaDeEncabezado(encabezado: string[]): string | null {
  const faltantes = COLUMNAS_ESPERADAS.filter((columna) => !encabezado.includes(columna))
  const sobrantes = encabezado.filter((columna) => !COLUMNAS_ESPERADAS.includes(columna))
  const repetidas = encabezado.filter((columna, indice) => encabezado.indexOf(columna) !== indice)
  if (faltantes.length === 0 && sobrantes.length === 0 && repetidas.length === 0) {
    return null
  }
  const partes = [
    faltantes.length > 0 ? `faltan ${faltantes.join(', ')}` : null,
    sobrantes.length > 0 ? `sobran ${sobrantes.map((columna) => columna || '(vacía)').join(', ')}` : null,
    repetidas.length > 0 ? `se repiten ${repetidas.join(', ')}` : null,
  ].filter((parte) => parte !== null)
  return `El encabezado no coincide con las columnas esperadas: ${partes.join('; ')}.`
}

export function analizarCsv(nombreArchivo: string, tamanoBytes: number, contenido: ArrayBuffer | null): AnalisisCsv {
  const identificacion = interpretarNombreArchivo(nombreArchivo)
  const analisis: AnalisisCsv = { identificacion, encabezado: [], filasMuestra: [], totalFilas: 0, problemas: [], avisos: [] }
  if (identificacion === null) {
    analisis.problemas.push('El nombre debe tener la forma lecturas_T01_2026-11.csv (torre y mes).')
  }
  if (contenido === null || tamanoBytes > TAMANO_MAXIMO_BYTES) {
    analisis.problemas.push('El archivo supera el tamaño máximo de 5 MB.')
    return analisis
  }

  const contenidoCsv = leerContenidoCsv(contenido)
  if (contenidoCsv.tipo === 'codificacion_invalida') {
    analisis.problemas.push('El archivo no está codificado en UTF-8.')
    return analisis
  }
  if (contenidoCsv.tipo === 'vacio') {
    analisis.problemas.push('El archivo está vacío.')
    return analisis
  }

  const diferenciaDeEncabezado = describirDiferenciaDeEncabezado(
    contenidoCsv.encabezado.celdas.map((celda) => celda.toLowerCase()),
  )
  if (diferenciaDeEncabezado !== null) {
    analisis.problemas.push(diferenciaDeEncabezado)
  }
  if (contenidoCsv.filas.length === 0) {
    analisis.avisos.push('El archivo solo tiene el encabezado; no hay lecturas que cargar.')
  }
  analisis.encabezado = contenidoCsv.encabezado.celdas
  analisis.filasMuestra = contenidoCsv.filas.slice(0, FILAS_DE_MUESTRA).map((fila) => fila.celdas)
  analisis.totalFilas = contenidoCsv.filas.length
  return analisis
}
