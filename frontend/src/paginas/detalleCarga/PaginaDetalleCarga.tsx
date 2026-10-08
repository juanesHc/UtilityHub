import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { ErrorRecursoInexistente, ErrorSesionVencida } from '../../api/errores'
import type { Carga, CodigoServicio, MotivoRechazo, Rechazo } from '../../api/tipos'
import { EnlaceVolver } from '../../componentes/EnlaceVolver'
import { Paginacion } from '../../componentes/Paginacion'
import { PastillaEstadoCarga } from '../../componentes/PastillaEstadoCarga'
import {
  formatearFechaHora,
  formatearNumero,
  formatearPeriodoLargo,
  fraseDeCarga,
  pluralizar,
  presentarServicio,
} from '../../dominio/formato'
import { rutaMedio } from '../../dominio/medios'
import { explicarMotivo } from '../../dominio/motivosRechazo'
import { useSesion } from '../../sesion/contextoSesion'
import { ContenidoArchivo } from './ContenidoArchivo'
import './detalleCarga.css'

const FILAS_POR_PAGINA = 20

interface DatosDetalleCarga {
  carga: Carga
  rechazos: Rechazo[]
  cargaVigente: Carga | null
}

type EstadoDetalleCarga =
  | { tipo: 'cargando' }
  | { tipo: 'listo'; datos: DatosDetalleCarga }
  | { tipo: 'inexistente' }
  | { tipo: 'error' }

interface RespuestaDetalleCarga {
  idCarga: number
  estado: EstadoDetalleCarga
}

interface GrupoDeMotivo {
  motivo: MotivoRechazo
  cantidad: number
}

function leerIdCarga(texto: string | undefined): number | null {
  const id = Number(texto)
  return Number.isInteger(id) && id > 0 ? id : null
}

function agruparPorMotivo(rechazos: Rechazo[]): GrupoDeMotivo[] {
  const conteo = new Map<MotivoRechazo, number>()
  for (const rechazo of rechazos) {
    conteo.set(rechazo.motivo, (conteo.get(rechazo.motivo) ?? 0) + 1)
  }
  return [...conteo.entries()].map(([motivo, cantidad]) => ({ motivo, cantidad })).sort((a, b) => b.cantidad - a.cantidad)
}

function esCodigoServicio(texto: string | null): texto is CodigoServicio {
  return texto === 'AGUA' || texto === 'ENERGIA'
}

function CeldaServicio({ servicio }: { servicio: string | null }) {
  if (servicio === null) {
    return <span className="detalle-carga-vacio">—</span>
  }
  if (!esCodigoServicio(servicio)) {
    return <span className="detalle-carga-mono">{servicio}</span>
  }
  const presentacion = presentarServicio(servicio)
  return (
    <span className="detalle-carga-servicio">
      <span className="punto" style={{ background: presentacion.variableColor }} />
      {presentacion.nombreVisible}
    </span>
  )
}

async function cargarDatos(
  listarCargas: () => Promise<Carga[]>,
  listarRechazos: (idCarga: number) => Promise<Rechazo[]>,
  idCarga: number,
): Promise<DatosDetalleCarga | null> {
  const [cargas, rechazos] = await Promise.all([listarCargas(), listarRechazos(idCarga)])
  const carga = cargas.find((candidata) => candidata.id_carga === idCarga)
  if (carga === undefined) {
    return null
  }
  const cargaVigente =
    carga.estado === 'reemplazada'
      ? (cargas.find(
          (candidata) =>
            candidata.codigo_torre === carga.codigo_torre && candidata.periodo === carga.periodo && candidata.estado !== 'reemplazada',
        ) ?? null)
      : null
  return { carga, rechazos, cargaVigente }
}

function Heroe({ carga }: { carga: Carga | null }) {
  const totalFilas = carga === null ? 0 : carga.filas_aceptadas + carga.filas_rechazadas
  return (
    <section className="detalle-carga-heroe">
      <div className="detalle-carga-heroe__fondo anim-acercamiento">
        <img src={rutaMedio('water-meters.jpg')} alt="" className="detalle-carga-heroe__foto" />
      </div>
      <div className="detalle-carga-heroe__degradado" />
      <div className="detalle-carga-heroe__contenido">
        <div className="detalle-carga-heroe__texto">
          <EnlaceVolver destinoPorDefecto="/cargas" texto="Volver a las cargas" className="detalle-carga-volver detalle-carga-ascenso-1" />
          <p className="etiqueta-mono detalle-carga-heroe__etiqueta detalle-carga-ascenso-1">Carga de archivo</p>
          {carga === null ? (
            <h1 className="detalle-carga-heroe__titular detalle-carga-heroe__titular--cargando">Detalle de la carga</h1>
          ) : (
            <>
              <h1 className="detalle-carga-heroe__titular detalle-carga-ascenso-2">
                {carga.nombre_torre}
                <br />
                {formatearPeriodoLargo(carga.periodo)}
              </h1>
              <p className="detalle-carga-heroe__archivo detalle-carga-ascenso-2">{carga.nombre_archivo}</p>
            </>
          )}
        </div>
        {carga !== null && (
          <div className="detalle-carga-heroe__cifra detalle-carga-ascenso-3">
            <div
              className={
                carga.filas_rechazadas > 0 ? 'detalle-carga-heroe__valor detalle-carga-heroe__valor--rechazos' : 'detalle-carga-heroe__valor detalle-carga-heroe__valor--limpio'
              }
            >
              {formatearNumero(carga.filas_rechazadas, 0)}
            </div>
            <div className="detalle-carga-heroe__descripcion">
              {carga.filas_rechazadas === 0
                ? 'filas rechazadas · todo en orden'
                : `${pluralizar(carga.filas_rechazadas, 'fila rechazada', 'filas rechazadas')} de ${formatearNumero(totalFilas, 0)}`}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function Resumen({ carga, cargaVigente }: { carga: Carga; cargaVigente: Carga | null }) {
  const totalFilas = carga.filas_aceptadas + carga.filas_rechazadas
  const porcentajeAceptadas = `${((carga.filas_aceptadas / (totalFilas || 1)) * 100).toFixed(1)}%`
  const porcentajeRechazadas = `${((carga.filas_rechazadas / (totalFilas || 1)) * 100).toFixed(1)}%`
  return (
    <section className="detalle-carga-seccion">
      {carga.estado === 'reemplazada' && (
        <div className="detalle-carga-aviso" role="note">
          <p>
            Este archivo fue reemplazado por uno más reciente de la misma torre y periodo. Sus lecturas se borraron al reprocesar;
            las filas rechazadas se conservan para consulta.
          </p>
          {cargaVigente !== null && (
            <Link to={`/cargas/${cargaVigente.id_carga}`} className="detalle-carga-aviso__enlace">
              Ver la carga vigente →
            </Link>
          )}
        </div>
      )}
      <dl className="detalle-carga-datos">
        <div className="detalle-carga-datos__celda">
          <dt>Archivo</dt>
          <dd className="detalle-carga-datos__valor detalle-carga-datos__valor--mono">{carga.nombre_archivo}</dd>
        </div>
        <div className="detalle-carga-datos__celda">
          <dt>Procesada</dt>
          <dd className="detalle-carga-datos__valor detalle-carga-datos__valor--mono">
            {formatearFechaHora(carga.fecha_procesamiento)}
          </dd>
        </div>
        <div className="detalle-carga-datos__celda">
          <dt>Estado</dt>
          <dd className="detalle-carga-datos__valor">
            <PastillaEstadoCarga estado={carga.estado} />
          </dd>
        </div>
        <div className="detalle-carga-datos__celda">
          <dt>Filas aceptadas</dt>
          <dd className="detalle-carga-datos__valor detalle-carga-datos__valor--mono">{formatearNumero(carga.filas_aceptadas, 0)}</dd>
        </div>
        <div className="detalle-carga-datos__celda">
          <dt>Filas rechazadas</dt>
          <dd
            className={
              carga.filas_rechazadas > 0
                ? 'detalle-carga-datos__valor detalle-carga-datos__valor--mono detalle-carga-datos__valor--rechazos'
                : 'detalle-carga-datos__valor detalle-carga-datos__valor--mono'
            }
          >
            {formatearNumero(carga.filas_rechazadas, 0)}
          </dd>
        </div>
      </dl>
      <div className="detalle-carga-resultado">
        <p className="detalle-carga-resultado__frase">{fraseDeCarga(carga.estado, carga.filas_aceptadas, carga.filas_rechazadas)}</p>
        <div className="detalle-carga-barra" role="img" aria-label={`${carga.filas_aceptadas} filas aceptadas y ${carga.filas_rechazadas} rechazadas`}>
          <span style={{ width: porcentajeAceptadas }}>
            <span className="detalle-carga-barra__relleno detalle-carga-barra__relleno--aceptadas" />
          </span>
          <span style={{ width: porcentajeRechazadas }}>
            <span className="detalle-carga-barra__relleno detalle-carga-barra__relleno--rechazadas" />
          </span>
        </div>
      </div>
    </section>
  )
}

function Rechazos({ carga, rechazos }: { carga: Carga; rechazos: Rechazo[] }) {
  const [motivoSeleccionado, establecerMotivoSeleccionado] = useState<MotivoRechazo | null>(null)
  const [pagina, establecerPagina] = useState(1)
  const grupos = agruparPorMotivo(rechazos)
  const visibles = motivoSeleccionado === null ? rechazos : rechazos.filter((rechazo) => rechazo.motivo === motivoSeleccionado)
  const totalPaginas = Math.max(1, Math.ceil(visibles.length / FILAS_POR_PAGINA))
  const paginaActual = Math.min(pagina, totalPaginas)
  const filasDeLaPagina = visibles.slice((paginaActual - 1) * FILAS_POR_PAGINA, paginaActual * FILAS_POR_PAGINA)

  function seleccionarMotivo(motivo: MotivoRechazo | null) {
    establecerMotivoSeleccionado(motivo)
    establecerPagina(1)
  }

  if (rechazos.length === 0) {
    return (
      <section className="detalle-carga-seccion detalle-carga-seccion--rechazos">
        <div className="detalle-carga-limpio">
          <h2 className="detalle-carga-limpio__titulo">Todas las filas pasaron la validación</h2>
          <p className="detalle-carga-limpio__texto">
            {carga.estado === 'reemplazada'
              ? 'Este archivo no tuvo filas rechazadas antes de ser reemplazado.'
              : 'No hay nada que corregir en este archivo.'}
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="detalle-carga-seccion detalle-carga-seccion--rechazos">
      <p className="etiqueta-mono detalle-carga-etiqueta">Filas rechazadas</p>
      <h2 className="detalle-carga-titulo">Qué corregir en el archivo</h2>
      <p className="detalle-carga-introduccion">
        {grupos.length === 1
          ? 'Todas las filas rechazadas comparten el mismo motivo.'
          : `Las filas rechazadas se agrupan en ${grupos.length} motivos. Elige uno para ver solo esas filas.`}{' '}
        Si este es el periodo más reciente de la torre, al volver a cargar el archivo corregido reemplazará a esta carga.
      </p>

      <ul className="detalle-carga-motivos">
        {grupos.map((grupo) => {
          const explicacion = explicarMotivo(grupo.motivo)
          const seleccionado = motivoSeleccionado === grupo.motivo
          return (
            <li key={grupo.motivo}>
              <button
                type="button"
                className="detalle-carga-motivo"
                aria-pressed={seleccionado}
                onClick={() => seleccionarMotivo(seleccionado ? null : grupo.motivo)}
              >
                <span className="detalle-carga-motivo__cantidad">{formatearNumero(grupo.cantidad, 0)}</span>
                <span className="detalle-carga-motivo__texto">
                  <span className="detalle-carga-motivo__titulo">{explicacion.titulo}</span>
                  <span className="detalle-carga-motivo__correccion">{explicacion.comoCorregir}</span>
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      <div className="detalle-carga-resumen-tabla" aria-live="polite">
        <span>
          <strong>{formatearNumero(visibles.length, 0)}</strong> {pluralizar(visibles.length, 'fila', 'filas')}
          {motivoSeleccionado === null ? ' · en el orden del archivo' : ` · ${explicarMotivo(motivoSeleccionado).titulo.toLowerCase()}`}
        </span>
        {motivoSeleccionado !== null && (
          <button type="button" className="detalle-carga-boton-enlace" onClick={() => seleccionarMotivo(null)}>
            Ver todas
          </button>
        )}
      </div>
      <div className="detalle-carga-tabla-contenedor">
        <table className="detalle-carga-tabla">
          <caption className="visualmente-oculto">Filas rechazadas del archivo {carga.nombre_archivo}</caption>
          <thead>
            <tr>
              <th scope="col" className="detalle-carga-celda-numero">Fila</th>
              <th scope="col">Apto</th>
              <th scope="col">Servicio</th>
              <th scope="col">Periodo</th>
              <th scope="col">Motivo</th>
              <th scope="col">Valor recibido</th>
            </tr>
          </thead>
          <tbody>
            {filasDeLaPagina.map((rechazo) => (
              <tr key={rechazo.id_rechazo} className="detalle-carga-fila">
                <td className="detalle-carga-celda-numero">{rechazo.numero_fila}</td>
                <td>{rechazo.apartamento ?? <span className="detalle-carga-vacio">—</span>}</td>
                <td>
                  <CeldaServicio servicio={rechazo.servicio} />
                </td>
                <td className="detalle-carga-mono">{rechazo.periodo ?? <span className="detalle-carga-vacio">—</span>}</td>
                <td className="detalle-carga-celda-motivo">{explicarMotivo(rechazo.motivo).titulo}</td>
                <td className="detalle-carga-mono detalle-carga-celda-valor">
                  {rechazo.valor_recibido ?? <span className="detalle-carga-vacio">vacío</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="detalle-carga-nota">
        El número de fila cuenta la línea de encabezado: la fila 2 es la primera lectura del archivo.
      </p>
      <Paginacion etiqueta="Páginas de filas rechazadas" paginaActual={paginaActual} totalPaginas={totalPaginas} alCambiarPagina={establecerPagina} />
    </section>
  )
}

export function PaginaDetalleCarga() {
  const { cliente } = useSesion()
  const { idCarga: textoId } = useParams()
  const idCarga = leerIdCarga(textoId)
  const [respuesta, establecerRespuesta] = useState<RespuestaDetalleCarga | null>(null)
  const [intento, establecerIntento] = useState(0)

  useEffect(() => {
    if (idCarga === null) {
      return undefined
    }
    let vigente = true
    cargarDatos(
      () => cliente.listarCargas(),
      (id) => cliente.listarRechazosDeCarga(id),
      idCarga,
    )
      .then((datos) => {
        if (vigente) {
          establecerRespuesta({ idCarga, estado: datos === null ? { tipo: 'inexistente' } : { tipo: 'listo', datos } })
        }
      })
      .catch((error: unknown) => {
        if (!vigente || error instanceof ErrorSesionVencida) {
          return
        }
        establecerRespuesta({ idCarga, estado: error instanceof ErrorRecursoInexistente ? { tipo: 'inexistente' } : { tipo: 'error' } })
      })
    return () => {
      vigente = false
    }
  }, [cliente, idCarga, intento])

  const estado: EstadoDetalleCarga =
    idCarga === null ? { tipo: 'inexistente' } : respuesta?.idCarga === idCarga ? respuesta.estado : { tipo: 'cargando' }
  const datos = estado.tipo === 'listo' ? estado.datos : null

  return (
    <div className="detalle-carga">
      <Heroe carga={datos?.carga ?? null} />

      {estado.tipo === 'cargando' && (
        <section className="detalle-carga-seccion">
          <p className="detalle-carga-estado" aria-live="polite">
            Cargando la carga…
          </p>
        </section>
      )}

      {estado.tipo === 'inexistente' && (
        <section className="detalle-carga-seccion">
          <div className="detalle-carga-aviso" role="alert">
            <p>Esta carga no existe o ya no está disponible.</p>
            <Link to="/cargas" className="detalle-carga-aviso__enlace">
              Ir a las cargas
            </Link>
          </div>
        </section>
      )}

      {estado.tipo === 'error' && (
        <section className="detalle-carga-seccion">
          <div className="detalle-carga-aviso detalle-carga-aviso--error" role="alert">
            <p>No pudimos cargar el detalle de la carga.</p>
            <button
              type="button"
              className="detalle-carga-boton-secundario"
              onClick={() => {
                establecerRespuesta(null)
                establecerIntento((actual) => actual + 1)
              }}
            >
              Reintentar
            </button>
          </div>
        </section>
      )}

      {datos !== null && (
        <>
          <Resumen carga={datos.carga} cargaVigente={datos.cargaVigente} />
          <Rechazos key={datos.carga.id_carga} carga={datos.carga} rechazos={datos.rechazos} />
          <ContenidoArchivo carga={datos.carga} rechazos={datos.rechazos} />
        </>
      )}
    </div>
  )
}
