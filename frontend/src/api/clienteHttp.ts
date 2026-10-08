import {
  ErrorConexion,
  ErrorConflicto,
  ErrorCredencialesInvalidas,
  ErrorCuentaBloqueada,
  ErrorEnvioArchivo,
  ErrorRecursoInexistente,
  ErrorServidor,
  ErrorSesionVencida,
  ErrorSolicitudInvalida,
} from './errores'
import type {
  AdministradorListado,
  ArchivoDeCarga,
  Carga,
  ClienteApi,
  DetalleLectura,
  FiltrosHistorico,
  PaginaHistorico,
  Rechazo,
  Servicio,
  Subida,
  SubidaAutorizada,
  TokenAcceso,
  Torre,
  UsuarioRegistrado,
} from './tipos'

const SEGUNDOS_POR_MINUTO = 60
const PATRON_MINUTOS_EN_MENSAJE = /(\d+)\s*minuto/

interface OpcionesPeticion {
  metodo?: 'GET' | 'POST'
  cuerpo?: unknown
  requiereSesion?: boolean
}

export class ClienteHttp implements ClienteApi {
  private readonly urlBase: string
  private readonly obtenerToken: () => string | null

  constructor(urlBase: string, obtenerToken: () => string | null) {
    this.urlBase = urlBase.replace(/\/+$/, '')
    this.obtenerToken = obtenerToken
  }

  iniciarSesion(usuario: string, clave: string): Promise<TokenAcceso> {
    return this.pedir<TokenAcceso>('/api/auth/login', {
      metodo: 'POST',
      cuerpo: { usuario, clave },
      requiereSesion: false,
    })
  }

  consultarHistorico(filtros: FiltrosHistorico): Promise<PaginaHistorico> {
    return this.pedir<PaginaHistorico>(`/api/lecturas${construirConsulta(filtros)}`)
  }

  obtenerDetalleLectura(idLectura: number): Promise<DetalleLectura> {
    return this.pedir<DetalleLectura>(`/api/lecturas/${idLectura}`)
  }

  listarCargas(): Promise<Carga[]> {
    return this.pedir<Carga[]>('/api/cargas')
  }

  listarRechazosDeCarga(idCarga: number): Promise<Rechazo[]> {
    return this.pedir<Rechazo[]>(`/api/cargas/${idCarga}/rechazos`)
  }

  listarTorres(): Promise<Torre[]> {
    return this.pedir<Torre[]>('/api/torres')
  }

  listarServicios(): Promise<Servicio[]> {
    return this.pedir<Servicio[]>('/api/servicios')
  }

  registrarUsuario(usuario: string, clave: string): Promise<UsuarioRegistrado> {
    return this.pedir<UsuarioRegistrado>('/api/usuarios', { metodo: 'POST', cuerpo: { usuario, clave } })
  }

  listarAdministradores(): Promise<AdministradorListado[]> {
    return this.pedir<AdministradorListado[]>('/api/usuarios')
  }

  solicitarSubida(nombreArchivo: string): Promise<SubidaAutorizada> {
    return this.pedir<SubidaAutorizada>('/api/subidas', { metodo: 'POST', cuerpo: { nombre_archivo: nombreArchivo } })
  }

  async enviarArchivo(autorizacion: SubidaAutorizada, archivo: File): Promise<void> {
    let respuesta: Response
    try {
      respuesta = await fetch(autorizacion.url_subida, {
        method: autorizacion.metodo,
        headers: autorizacion.encabezados,
        body: archivo,
      })
    } catch {
      throw new ErrorEnvioArchivo(null)
    }
    if (!respuesta.ok) {
      throw new ErrorEnvioArchivo(respuesta.status)
    }
  }

  consultarSubida(idSubida: number): Promise<Subida> {
    return this.pedir<Subida>(`/api/subidas/${idSubida}`)
  }

  obtenerArchivoDeCarga(idCarga: number): Promise<ArchivoDeCarga> {
    return this.pedir<ArchivoDeCarga>(`/api/cargas/${idCarga}/archivo`)
  }

  async descargarArchivo(archivo: ArchivoDeCarga): Promise<ArrayBuffer> {
    let respuesta: Response
    try {
      respuesta = await fetch(archivo.url_descarga)
    } catch {
      throw new ErrorConexion()
    }
    if (!respuesta.ok) {
      throw new ErrorServidor(respuesta.status)
    }
    return respuesta.arrayBuffer()
  }

  private async pedir<Respuesta>(ruta: string, opciones: OpcionesPeticion = {}): Promise<Respuesta> {
    const requiereSesion = opciones.requiereSesion ?? true
    const encabezados: Record<string, string> = { Accept: 'application/json' }
    if (opciones.cuerpo !== undefined) {
      encabezados['Content-Type'] = 'application/json'
    }
    const token = requiereSesion ? this.obtenerToken() : null
    if (requiereSesion && token === null) {
      throw new ErrorSesionVencida()
    }
    if (token !== null) {
      encabezados.Authorization = `Bearer ${token}`
    }

    let respuesta: Response
    try {
      respuesta = await fetch(`${this.urlBase}${ruta}`, {
        method: opciones.metodo ?? 'GET',
        headers: encabezados,
        body: opciones.cuerpo === undefined ? undefined : JSON.stringify(opciones.cuerpo),
      })
    } catch {
      throw new ErrorConexion()
    }

    if (respuesta.ok) {
      return (await respuesta.json()) as Respuesta
    }
    throw await traducirRespuestaDeError(respuesta, requiereSesion)
  }
}

function construirConsulta(filtros: FiltrosHistorico): string {
  const parametros = new URLSearchParams()
  for (const [nombre, valor] of Object.entries(filtros)) {
    if (valor === undefined || valor === '' || valor === false) {
      continue
    }
    parametros.set(nombre, String(valor))
  }
  const consulta = parametros.toString()
  return consulta === '' ? '' : `?${consulta}`
}

async function leerDetalle(respuesta: Response): Promise<string> {
  try {
    const cuerpo: unknown = await respuesta.json()
    if (typeof cuerpo === 'object' && cuerpo !== null && 'detail' in cuerpo) {
      const detalle = (cuerpo as { detail: unknown }).detail
      if (typeof detalle === 'string') {
        return detalle
      }
      if (Array.isArray(detalle)) {
        return 'Algunos datos enviados no son válidos.'
      }
    }
  } catch {
    return respuesta.statusText
  }
  return respuesta.statusText
}

function calcularSegundosDeBloqueo(respuesta: Response, detalle: string): number {
  const reintentarDespues = Number(respuesta.headers.get('Retry-After'))
  if (Number.isFinite(reintentarDespues) && reintentarDespues > 0) {
    return reintentarDespues
  }
  const minutosEnMensaje = PATRON_MINUTOS_EN_MENSAJE.exec(detalle)?.[1]
  return minutosEnMensaje === undefined ? SEGUNDOS_POR_MINUTO : Number(minutosEnMensaje) * SEGUNDOS_POR_MINUTO
}

async function traducirRespuestaDeError(respuesta: Response, requiereSesion: boolean): Promise<Error> {
  const detalle = await leerDetalle(respuesta)
  switch (respuesta.status) {
    case 401:
      return requiereSesion ? new ErrorSesionVencida() : new ErrorCredencialesInvalidas()
    case 404:
      return new ErrorRecursoInexistente(detalle)
    case 409:
      return new ErrorConflicto(detalle)
    case 422:
      return new ErrorSolicitudInvalida(detalle)
    case 429:
      return new ErrorCuentaBloqueada(calcularSegundosDeBloqueo(respuesta, detalle))
    default:
      return new ErrorServidor(respuesta.status)
  }
}
