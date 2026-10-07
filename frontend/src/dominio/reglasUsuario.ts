export const LONGITUD_MAXIMA_NOMBRE_USUARIO = 50
export const LONGITUD_MINIMA_CLAVE = 12
export const LONGITUD_MAXIMA_CLAVE = 128

const CARACTERES_DE_CLAVE_GENERADA = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
const GRUPOS_DE_CLAVE_GENERADA = 4
const CARACTERES_POR_GRUPO = 4
const PRIMER_CARACTER_IMPRIMIBLE = 0x20
const INICIO_CONTROLES_EXTENDIDOS = 0x7f
const FIN_CONTROLES_EXTENDIDOS = 0x9f

function contieneCaracterDeControl(texto: string): boolean {
  return [...texto].some((caracter) => {
    const codigo = caracter.codePointAt(0) ?? 0
    return codigo < PRIMER_CARACTER_IMPRIMIBLE || (codigo >= INICIO_CONTROLES_EXTENDIDOS && codigo <= FIN_CONTROLES_EXTENDIDOS)
  })
}

export interface ReglaCumplida {
  identificador: string
  descripcion: string
  cumplida: boolean
}

export function reglasDeNombre(nombreUsuario: string): ReglaCumplida[] {
  return [
    {
      identificador: 'nombre-no-vacio',
      descripcion: `Entre 1 y ${LONGITUD_MAXIMA_NOMBRE_USUARIO} caracteres`,
      cumplida: nombreUsuario.length >= 1 && nombreUsuario.length <= LONGITUD_MAXIMA_NOMBRE_USUARIO,
    },
    {
      identificador: 'nombre-sin-espacios-en-los-bordes',
      descripcion: 'Sin espacios al inicio ni al final',
      cumplida: nombreUsuario !== '' && nombreUsuario === nombreUsuario.trim(),
    },
    {
      identificador: 'nombre-sin-caracteres-de-control',
      descripcion: 'Sin tabuladores ni caracteres invisibles',
      cumplida: nombreUsuario !== '' && !contieneCaracterDeControl(nombreUsuario),
    },
  ]
}

export function reglasDeClave(clave: string, confirmacion: string): ReglaCumplida[] {
  return [
    {
      identificador: 'clave-longitud',
      descripcion: `Entre ${LONGITUD_MINIMA_CLAVE} y ${LONGITUD_MAXIMA_CLAVE} caracteres`,
      cumplida: clave.length >= LONGITUD_MINIMA_CLAVE && clave.length <= LONGITUD_MAXIMA_CLAVE,
    },
    {
      identificador: 'clave-sin-nul',
      descripcion: 'Sin caracteres invisibles',
      cumplida: clave !== '' && !clave.includes('\u0000'),
    },
    {
      identificador: 'clave-coincide',
      descripcion: 'La confirmación coincide',
      cumplida: confirmacion !== '' && clave === confirmacion,
    },
  ]
}

export function todasCumplidas(reglas: ReglaCumplida[]): boolean {
  return reglas.every((regla) => regla.cumplida)
}

function caracterAleatorio(): string {
  const limite = Math.floor(256 / CARACTERES_DE_CLAVE_GENERADA.length) * CARACTERES_DE_CLAVE_GENERADA.length
  const byte = new Uint8Array(1)
  do {
    crypto.getRandomValues(byte)
  } while ((byte[0] ?? 0) >= limite)
  return CARACTERES_DE_CLAVE_GENERADA[(byte[0] ?? 0) % CARACTERES_DE_CLAVE_GENERADA.length] ?? 'x'
}

export function generarClaveSegura(): string {
  return Array.from({ length: GRUPOS_DE_CLAVE_GENERADA }, () =>
    Array.from({ length: CARACTERES_POR_GRUPO }, caracterAleatorio).join(''),
  ).join('-')
}
