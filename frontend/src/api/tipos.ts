export type CodigoServicio = 'AGUA' | 'ENERGIA'

export type EstadoCarga = 'procesada_completa' | 'procesada_parcial' | 'rechazada' | 'reemplazada'

export type MotivoRechazo =
  | 'columnas_sobrantes'
  | 'campo_obligatorio_faltante'
  | 'tripleta_repetida_en_archivo'
  | 'torre_distinta_a_la_del_archivo'
  | 'periodo_distinto_al_del_archivo'
  | 'lectura_no_numerica'
  | 'lectura_fuera_de_rango'
  | 'fecha_lectura_invalida'
  | 'apartamento_inexistente'
  | 'servicio_inexistente'
  | 'lectura_menor_que_la_anterior'

export interface TokenAcceso {
  token_acceso: string
  tipo_token: 'bearer'
  expira_en: string
  duracion_segundos: number
}

export interface LecturaHistorico {
  id_lectura: number
  codigo_torre: string
  nombre_torre: string
  numero_apartamento: string
  codigo_servicio: CodigoServicio
  nombre_servicio: string
  unidad_medida: string
  periodo: string
  lectura_acumulada: number
  consumo_periodo: number | null
  fecha_lectura: string
  promedio_referencia: number | null
  es_anomalo: boolean
}

export interface PaginaHistorico {
  lecturas: LecturaHistorico[]
  pagina: number
  tamano_pagina: number
  total_resultados: number
  total_paginas: number
}

export interface FiltrosHistorico {
  torre?: string
  apartamento?: string
  servicio?: string
  periodo_desde?: string
  periodo_hasta?: string
  solo_anomalos?: boolean
  pagina?: number
  tamano_pagina?: number
}

export interface DetalleLectura {
  id_lectura: number
  id_carga: number
  codigo_torre: string
  nombre_torre: string
  numero_apartamento: string
  codigo_servicio: CodigoServicio
  nombre_servicio: string
  unidad_medida: string
  periodo: string
  fecha_lectura: string
  lectura_acumulada: number
  consumo_periodo: number | null
  promedio_referencia: number | null
  umbral_desviacion: number
  limite_inferior_normal: number | null
  limite_superior_normal: number | null
  desviacion_relativa: number | null
  fue_evaluada: boolean
  es_anomalo: boolean
}

export interface Carga {
  id_carga: number
  codigo_torre: string
  nombre_torre: string
  periodo: string
  nombre_archivo: string
  fecha_procesamiento: string
  estado: EstadoCarga
  filas_aceptadas: number
  filas_rechazadas: number
}

export interface Rechazo {
  id_rechazo: number
  numero_fila: number
  apartamento: string | null
  servicio: string | null
  periodo: string | null
  motivo: MotivoRechazo
  valor_recibido: string | null
}

export interface Torre {
  id_torre: number
  codigo: string
  nombre: string
}

export interface Servicio {
  id_servicio: number
  codigo: CodigoServicio
  nombre: string
  unidad_medida: string
  umbral_desviacion: number
}

export interface UsuarioRegistrado {
  id_usuario: number
  nombre_usuario: string
  fecha_creacion: string
  creado_por: string | null
}

export interface AdministradorListado {
  id_usuario: number
  nombre_usuario: string
  fecha_creacion: string | null
  creado_por: string | null
  ultimo_acceso: string | null
  esta_bloqueado: boolean
}

export type EstadoSubida = 'pendiente' | 'procesada' | 'fallida'

export interface SubidaAutorizada {
  id_subida: number
  clave_objeto: string
  url_subida: string
  metodo: 'PUT'
  encabezados: Record<string, string>
  expira_en: string
}

export interface Subida {
  id_subida: number
  nombre_archivo: string
  estado: EstadoSubida
  fecha_solicitud: string
  id_carga: number | null
  detalle_error: string | null
  fecha_procesamiento: string | null
}

export interface ArchivoDeCarga {
  nombre_archivo: string
  url_descarga: string
  expira_en: string
}

export interface ClienteApi {
  iniciarSesion(usuario: string, clave: string): Promise<TokenAcceso>
  consultarHistorico(filtros: FiltrosHistorico): Promise<PaginaHistorico>
  obtenerDetalleLectura(idLectura: number): Promise<DetalleLectura>
  listarCargas(): Promise<Carga[]>
  listarRechazosDeCarga(idCarga: number): Promise<Rechazo[]>
  listarTorres(): Promise<Torre[]>
  listarServicios(): Promise<Servicio[]>
  registrarUsuario(usuario: string, clave: string): Promise<UsuarioRegistrado>
  listarAdministradores(): Promise<AdministradorListado[]>
  solicitarSubida(nombreArchivo: string): Promise<SubidaAutorizada>
  enviarArchivo(autorizacion: SubidaAutorizada, archivo: File): Promise<void>
  consultarSubida(idSubida: number): Promise<Subida>
  obtenerArchivoDeCarga(idCarga: number): Promise<ArchivoDeCarga>
  descargarArchivo(archivo: ArchivoDeCarga): Promise<ArrayBuffer>
}
