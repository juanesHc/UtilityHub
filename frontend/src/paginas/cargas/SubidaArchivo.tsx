import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { Link } from 'react-router'
import { ErrorApi, ErrorServidor, ErrorSesionVencida } from '../../api/errores'
import type { Subida, Torre } from '../../api/tipos'
import { useSesion } from '../../sesion/contextoSesion'
import { analizarCsv, TAMANO_MAXIMO_BYTES, type AnalisisCsv } from '../../dominio/analisisCsv'
import { VistaPreviaCsv } from './VistaPreviaCsv'
import './subida.css'

const INTERVALO_CONSULTA_MS = 1500
const CONSULTAS_MAXIMAS = 40

type Paso = 'permiso' | 'almacen' | 'procesamiento'
type EstadoPaso = 'pendiente' | 'activo' | 'hecho' | 'error'

type EstadoSubidaUi =
  | { fase: 'inactiva' }
  | { fase: 'leyendo'; nombreArchivo: string }
  | { fase: 'revisando'; archivo: File; analisis: AnalisisCsv }
  | { fase: 'en_curso'; nombreArchivo: string; paso: Paso }
  | { fase: 'procesada'; nombreArchivo: string; idCarga: number }
  | { fase: 'fallida'; nombreArchivo: string; paso: Paso; mensaje: string }
  | { fase: 'sin_respuesta'; nombreArchivo: string }

const PASOS: readonly { clave: Paso; titulo: string; descripcion: string }[] = [
  { clave: 'permiso', titulo: 'Permiso', descripcion: 'La API revisa el nombre y firma una URL temporal' },
  { clave: 'almacen', titulo: 'Almacén', descripcion: 'El navegador envía el archivo directo al almacén' },
  { clave: 'procesamiento', titulo: 'Procesamiento', descripcion: 'Se validan las filas y se guardan las lecturas' },
]

function esperar(milisegundos: number): Promise<void> {
  return new Promise((resolver) => window.setTimeout(resolver, milisegundos))
}

function estadoDelPaso(estado: EstadoSubidaUi, paso: Paso): EstadoPaso {
  const indicePaso = PASOS.findIndex((candidato) => candidato.clave === paso)
  switch (estado.fase) {
    case 'inactiva':
    case 'leyendo':
    case 'revisando':
      return 'pendiente'
    case 'procesada':
      return 'hecho'
    case 'sin_respuesta':
      return paso === 'procesamiento' ? 'activo' : 'hecho'
    case 'en_curso':
    case 'fallida': {
      const indiceActual = PASOS.findIndex((candidato) => candidato.clave === estado.paso)
      if (indicePaso < indiceActual) {
        return 'hecho'
      }
      if (indicePaso > indiceActual) {
        return 'pendiente'
      }
      return estado.fase === 'fallida' ? 'error' : 'activo'
    }
  }
}

function describirError(error: unknown): string {
  if (error instanceof ErrorServidor && error.codigoHttp === 503) {
    return 'La subida de archivos no está habilitada en este servidor.'
  }
  if (error instanceof ErrorApi) {
    return error.message
  }
  return 'Ocurrió un error inesperado.'
}

export function SubidaArchivo({ torres, onCargaRegistrada }: { torres: Torre[]; onCargaRegistrada: () => void }) {
  const { cliente } = useSesion()
  const [estado, establecerEstado] = useState<EstadoSubidaUi>({ fase: 'inactiva' })
  const selectorArchivo = useRef<HTMLInputElement>(null)
  const montado = useRef(true)

  useEffect(() => {
    montado.current = true
    return () => {
      montado.current = false
    }
  }, [])

  const enCurso = estado.fase === 'en_curso' || estado.fase === 'leyendo'

  async function esperarResultado(idSubida: number): Promise<Subida | null> {
    for (let consulta = 0; consulta < CONSULTAS_MAXIMAS && montado.current; consulta += 1) {
      const subida = await cliente.consultarSubida(idSubida)
      if (subida.estado !== 'pendiente') {
        return subida
      }
      await esperar(INTERVALO_CONSULTA_MS)
    }
    return null
  }

  async function subir(archivo: File) {
    const nombreArchivo = archivo.name
    let paso: Paso = 'permiso'
    establecerEstado({ fase: 'en_curso', nombreArchivo, paso })
    try {
      const autorizacion = await cliente.solicitarSubida(nombreArchivo)
      paso = 'almacen'
      establecerEstado({ fase: 'en_curso', nombreArchivo, paso })
      await cliente.enviarArchivo(autorizacion, archivo)
      paso = 'procesamiento'
      establecerEstado({ fase: 'en_curso', nombreArchivo, paso })
      const subida = await esperarResultado(autorizacion.id_subida)
      if (!montado.current) {
        return
      }
      if (subida === null) {
        establecerEstado({ fase: 'sin_respuesta', nombreArchivo })
      } else if (subida.estado === 'procesada' && subida.id_carga !== null) {
        establecerEstado({ fase: 'procesada', nombreArchivo, idCarga: subida.id_carga })
        onCargaRegistrada()
      } else {
        establecerEstado({
          fase: 'fallida',
          nombreArchivo,
          paso,
          mensaje: subida.detalle_error ?? 'El archivo no se pudo procesar.',
        })
      }
    } catch (error) {
      if (!montado.current) {
        return
      }
      if (error instanceof ErrorSesionVencida) {
        establecerEstado({ fase: 'inactiva' })
        return
      }
      establecerEstado({ fase: 'fallida', nombreArchivo, paso, mensaje: describirError(error) })
    }
  }

  async function revisar(archivo: File) {
    establecerEstado({ fase: 'leyendo', nombreArchivo: archivo.name })
    let contenido: ArrayBuffer | null = null
    if (archivo.size <= TAMANO_MAXIMO_BYTES) {
      try {
        contenido = await archivo.arrayBuffer()
      } catch {
        if (montado.current) {
          establecerEstado({ fase: 'fallida', nombreArchivo: archivo.name, paso: 'permiso', mensaje: 'No se pudo leer el archivo.' })
        }
        return
      }
    }
    if (montado.current) {
      establecerEstado({ fase: 'revisando', archivo, analisis: analizarCsv(archivo.name, archivo.size, contenido) })
    }
  }

  function alElegirArchivo(evento: ChangeEvent<HTMLInputElement>) {
    const archivo = evento.target.files?.[0]
    evento.target.value = ''
    if (archivo !== undefined) {
      void revisar(archivo)
    }
  }

  return (
    <section className="subida" aria-labelledby="subida-titulo">
      <div className="subida__cabecera">
        <div className="subida__texto">
          <h2 id="subida-titulo" className="subida__titulo">
            Subir lecturas
          </h2>
          <p className="subida__ayuda">
            Un archivo por torre y mes, con nombre como <code>lecturas_T01_2026-11.csv</code>. Máximo 5 MB.
          </p>
        </div>
        <input
          ref={selectorArchivo}
          id="subida-archivo"
          type="file"
          accept=".csv,text/csv"
          className="visualmente-oculto"
          tabIndex={-1}
          onChange={alElegirArchivo}
        />
        <button
          type="button"
          className={estado.fase === 'revisando' ? 'vista-previa__cancelar' : 'subida__boton'}
          disabled={enCurso}
          onClick={() => selectorArchivo.current?.click()}
        >
          {estado.fase === 'en_curso' ? 'Subiendo…' : estado.fase === 'revisando' ? 'Elegir otro archivo' : 'Elegir archivo CSV'}
        </button>
      </div>

      {estado.fase === 'leyendo' && <p className="subida__mensaje">Leyendo {estado.nombreArchivo}…</p>}

      {estado.fase === 'revisando' && (
        <div className="subida__progreso">
          <VistaPreviaCsv
            nombreArchivo={estado.archivo.name}
            tamanoBytes={estado.archivo.size}
            analisis={estado.analisis}
            torres={torres}
            onSubir={() => void subir(estado.archivo)}
            onCancelar={() => establecerEstado({ fase: 'inactiva' })}
          />
        </div>
      )}

      {(estado.fase === 'en_curso' || estado.fase === 'procesada' || estado.fase === 'fallida' || estado.fase === 'sin_respuesta') && (
        <div className="subida__progreso">
          <p className="subida__archivo">{estado.nombreArchivo}</p>
          <ol className="subida__pasos">
            {PASOS.map((paso, indice) => {
              const estadoPaso = estadoDelPaso(estado, paso.clave)
              return (
                <li key={paso.clave} className={`subida__paso subida__paso--${estadoPaso}`}>
                  <span className="subida__marcador" aria-hidden="true">
                    {estadoPaso === 'hecho' ? '✓' : estadoPaso === 'error' ? '!' : indice + 1}
                  </span>
                  <span className="subida__paso-texto">
                    <span className="subida__paso-titulo">{paso.titulo}</span>
                    <span className="subida__paso-descripcion">{paso.descripcion}</span>
                  </span>
                </li>
              )
            })}
          </ol>
          <div role="status" aria-live="polite" className="subida__resultado">
            {estado.fase === 'procesada' && (
              <p className="subida__mensaje subida__mensaje--ok">
                Archivo procesado. <Link to={`/cargas/${estado.idCarga}`}>Ver la carga</Link>
              </p>
            )}
            {estado.fase === 'fallida' && <p className="subida__mensaje subida__mensaje--error">{estado.mensaje}</p>}
            {estado.fase === 'sin_respuesta' && (
              <p className="subida__mensaje">
                El archivo llegó al almacén pero aún no termina de procesarse. Aparecerá en esta lista cuando esté listo.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
