import { useEffect, useMemo, useState } from 'react'
import { ErrorRecursoInexistente, ErrorServidor, ErrorSesionVencida } from '../../api/errores'
import type { Carga, MotivoRechazo, Rechazo } from '../../api/tipos'
import { Paginacion } from '../../componentes/Paginacion'
import { leerContenidoCsv, type ContenidoCsv, type FilaCsv } from '../../dominio/analisisCsv'
import { formatearNumero, pluralizar } from '../../dominio/formato'
import { explicarMotivo } from '../../dominio/motivosRechazo'
import { useSesion } from '../../sesion/contextoSesion'
import './contenidoArchivo.css'

const FILAS_POR_PAGINA = 20

type EstadoArchivo =
  | { tipo: 'cargando' }
  | { tipo: 'sin_archivo' }
  | { tipo: 'no_disponible' }
  | { tipo: 'error' }
  | { tipo: 'listo'; nombreArchivo: string; bytes: ArrayBuffer; contenido: ContenidoCsv }

interface RespuestaArchivo {
  idCarga: number
  estado: EstadoArchivo
}

function EnlaceDescarga({ nombreArchivo, bytes }: { nombreArchivo: string; bytes: ArrayBuffer }) {
  const url = useMemo(() => URL.createObjectURL(new Blob([bytes], { type: 'text/csv' })), [bytes])
  useEffect(() => () => URL.revokeObjectURL(url), [url])
  return (
    <a href={url} download={nombreArchivo} className="contenido-archivo__descarga">
      Descargar CSV
    </a>
  )
}

function TablaContenido({
  encabezado,
  filas,
  motivoPorLinea,
}: {
  encabezado: FilaCsv
  filas: FilaCsv[]
  motivoPorLinea: Map<number, MotivoRechazo>
}) {
  const [soloRechazadas, establecerSoloRechazadas] = useState(false)
  const [pagina, establecerPagina] = useState(1)
  const rechazadas = filas.filter((fila) => motivoPorLinea.has(fila.numeroLinea))
  const visibles = soloRechazadas ? rechazadas : filas
  const totalPaginas = Math.max(1, Math.ceil(visibles.length / FILAS_POR_PAGINA))
  const paginaActual = Math.min(pagina, totalPaginas)
  const filasDeLaPagina = visibles.slice((paginaActual - 1) * FILAS_POR_PAGINA, paginaActual * FILAS_POR_PAGINA)
  const columnas = encabezado.celdas.length

  function mostrarSoloRechazadas(valor: boolean) {
    establecerSoloRechazadas(valor)
    establecerPagina(1)
  }

  return (
    <>
      <div className="contenido-archivo__filtros" role="group" aria-label="Filas a mostrar">
        <button type="button" className="contenido-archivo__filtro" aria-pressed={!soloRechazadas} onClick={() => mostrarSoloRechazadas(false)}>
          Todas <span className="contenido-archivo__conteo">{formatearNumero(filas.length, 0)}</span>
        </button>
        {rechazadas.length > 0 && (
          <button type="button" className="contenido-archivo__filtro" aria-pressed={soloRechazadas} onClick={() => mostrarSoloRechazadas(true)}>
            Solo rechazadas <span className="contenido-archivo__conteo">{formatearNumero(rechazadas.length, 0)}</span>
          </button>
        )}
      </div>
      <div className="contenido-archivo__tabla-contenedor">
        <table className="contenido-archivo__tabla">
          <caption className="visualmente-oculto">Contenido del archivo, una fila por línea del CSV</caption>
          <thead>
            <tr>
              <th scope="col" className="contenido-archivo__linea">Línea</th>
              {encabezado.celdas.map((columna, indice) => (
                <th key={`${columna}-${indice}`} scope="col">
                  {columna}
                </th>
              ))}
              {rechazadas.length > 0 && <th scope="col">Motivo de rechazo</th>}
            </tr>
          </thead>
          <tbody>
            {filasDeLaPagina.map((fila) => {
              const motivo = motivoPorLinea.get(fila.numeroLinea)
              return (
                <tr key={fila.numeroLinea} className={motivo === undefined ? undefined : 'contenido-archivo__fila--rechazada'}>
                  <td className="contenido-archivo__linea">{fila.numeroLinea}</td>
                  {Array.from({ length: columnas }, (_, indiceColumna) => (
                    <td key={indiceColumna}>{fila.celdas[indiceColumna] ?? ''}</td>
                  ))}
                  {rechazadas.length > 0 && (
                    <td className="contenido-archivo__motivo">{motivo === undefined ? '' : explicarMotivo(motivo).titulo}</td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <Paginacion etiqueta="Páginas del contenido del archivo" paginaActual={paginaActual} totalPaginas={totalPaginas} alCambiarPagina={establecerPagina} />
    </>
  )
}

export function ContenidoArchivo({ carga, rechazos }: { carga: Carga; rechazos: Rechazo[] }) {
  const { cliente } = useSesion()
  const [respuesta, establecerRespuesta] = useState<RespuestaArchivo | null>(null)
  const idCarga = carga.id_carga

  useEffect(() => {
    let vigente = true
    cliente
      .obtenerArchivoDeCarga(idCarga)
      .then(async (archivo) => {
        const bytes = await cliente.descargarArchivo(archivo)
        if (vigente) {
          establecerRespuesta({
            idCarga,
            estado: { tipo: 'listo', nombreArchivo: archivo.nombre_archivo, bytes, contenido: leerContenidoCsv(bytes) },
          })
        }
      })
      .catch((error: unknown) => {
        if (!vigente || error instanceof ErrorSesionVencida) {
          return
        }
        const estado: EstadoArchivo =
          error instanceof ErrorRecursoInexistente
            ? { tipo: 'sin_archivo' }
            : error instanceof ErrorServidor && error.codigoHttp === 503
              ? { tipo: 'no_disponible' }
              : { tipo: 'error' }
        establecerRespuesta({ idCarga, estado })
      })
    return () => {
      vigente = false
    }
  }, [cliente, idCarga])

  const motivoPorLinea = useMemo(
    () => new Map(rechazos.map((rechazo) => [rechazo.numero_fila, rechazo.motivo] as const)),
    [rechazos],
  )
  const estado: EstadoArchivo = respuesta?.idCarga === idCarga ? respuesta.estado : { tipo: 'cargando' }

  return (
    <section className="contenido-archivo" aria-labelledby="contenido-archivo-titulo">
      <div className="contenido-archivo__cabecera">
        <div>
          <p className="etiqueta-mono contenido-archivo__etiqueta">Archivo original</p>
          <h2 id="contenido-archivo-titulo" className="contenido-archivo__titulo">
            Contenido del archivo
          </h2>
          <p className="contenido-archivo__introduccion">
            Así llegó el CSV al almacén, línea por línea. Las filas rechazadas aparecen marcadas con su motivo.
          </p>
        </div>
        {estado.tipo === 'listo' && <EnlaceDescarga nombreArchivo={estado.nombreArchivo} bytes={estado.bytes} />}
      </div>

      {estado.tipo === 'cargando' && <p className="contenido-archivo__mensaje">Leyendo el archivo del almacén…</p>}
      {estado.tipo === 'sin_archivo' && (
        <p className="contenido-archivo__mensaje">
          Esta carga se procesó desde la línea de comandos, así que su archivo no quedó guardado en el almacén. Solo los
          archivos subidos desde la página Cargas se pueden consultar aquí.
        </p>
      )}
      {estado.tipo === 'no_disponible' && (
        <p className="contenido-archivo__mensaje">El almacén de archivos no está habilitado en este servidor.</p>
      )}
      {estado.tipo === 'error' && (
        <p className="contenido-archivo__mensaje contenido-archivo__mensaje--error" role="alert">
          No pudimos leer el archivo del almacén.
        </p>
      )}
      {estado.tipo === 'listo' && estado.contenido.tipo === 'codificacion_invalida' && (
        <p className="contenido-archivo__mensaje">El archivo no está en UTF-8, así que no se puede mostrar. Puedes descargarlo.</p>
      )}
      {estado.tipo === 'listo' && estado.contenido.tipo === 'vacio' && <p className="contenido-archivo__mensaje">El archivo está vacío.</p>}
      {estado.tipo === 'listo' && estado.contenido.tipo === 'legible' && (
        <>
          <p className="contenido-archivo__resumen">
            <strong>{formatearNumero(estado.contenido.filas.length, 0)}</strong>{' '}
            {pluralizar(estado.contenido.filas.length, 'fila', 'filas')} de datos · la línea 1 es el encabezado
          </p>
          <TablaContenido
            key={carga.id_carga}
            encabezado={estado.contenido.encabezado}
            filas={estado.contenido.filas}
            motivoPorLinea={motivoPorLinea}
          />
        </>
      )}
    </section>
  )
}
