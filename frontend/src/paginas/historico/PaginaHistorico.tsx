import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { ErrorSesionVencida } from '../../api/errores'
import type { LecturaHistorico, PaginaHistorico, Servicio, Torre } from '../../api/tipos'
import { Paginacion } from '../../componentes/Paginacion'
import { calcularDesviacionRelativa } from '../../dominio/evaluacion'
import {
  formatearConsumo,
  formatearDesviacion,
  formatearLecturaMedidor,
  formatearNumero,
  formatearPeriodoCorto,
  formatearPromedio,
  nombreCortoDeTorre,
  pluralizar,
  presentarServicio,
} from '../../dominio/formato'
import { prefiereMovimientoReducido, rutaMedio } from '../../dominio/medios'
import { useSesion } from '../../sesion/contextoSesion'
import {
  claveDeConsulta,
  convertirEnFiltrosDeApi,
  escribirFiltrosEnUrl,
  hayFiltrosActivos,
  leerFiltrosDeUrl,
  rangoDePeriodosInvertido,
  type CambiosDeFiltros,
} from './filtrosHistorico'
import './historico.css'

const ESPERA_APARTAMENTO_MILISEGUNDOS = 350
const RETRASO_POR_FILA_SEGUNDOS = 0.04
const MOTIVO_SIN_DATO =
  'No se puede calcular el consumo: es la primera lectura de este medidor (línea base) o falta la lectura del periodo anterior.'

interface Catalogos {
  torres: Torre[]
  servicios: Servicio[]
}

interface RespuestaConsulta {
  clave: string
  estado: 'lista' | 'error'
  pagina: PaginaHistorico | null
}

function InterruptorSoloAnomalos({ activo, alCambiar }: { activo: boolean; alCambiar: () => void }) {
  return (
    <button type="button" className="historico-interruptor" aria-pressed={activo} onClick={alCambiar}>
      <span className="historico-interruptor__pista" aria-hidden="true">
        <span className="historico-interruptor__relleno" />
        <span className="historico-interruptor__perilla" />
      </span>
      Solo anómalos
    </button>
  )
}

function CeldaEstado({ lectura, umbralPorServicio }: { lectura: LecturaHistorico; umbralPorServicio: Map<string, number> }) {
  if (lectura.es_anomalo) {
    const desviacion =
      lectura.consumo_periodo === null || lectura.promedio_referencia === null || !umbralPorServicio.has(lectura.codigo_servicio)
        ? null
        : calcularDesviacionRelativa(lectura.consumo_periodo, lectura.promedio_referencia)
    return (
      <span className="historico-pastilla-anomalia">
        Anómalo{desviacion === null ? '' : ` ${formatearDesviacion(desviacion)}`}
      </span>
    )
  }
  const sinEvaluar = lectura.consumo_periodo === null || lectura.promedio_referencia === null
  return <span className="historico-estado">{sinEvaluar ? 'Sin evaluar' : 'Normal'}</span>
}

function FilaLectura({
  lectura,
  indice,
  umbralPorServicio,
}: {
  lectura: LecturaHistorico
  indice: number
  umbralPorServicio: Map<string, number>
}) {
  const navegar = useNavigate()
  const presentacion = presentarServicio(lectura.codigo_servicio)
  const destino = `/lecturas/${lectura.id_lectura}`

  return (
    <tr
      className="historico-fila"
      style={{ animationDelay: `${(indice * RETRASO_POR_FILA_SEGUNDOS).toFixed(2)}s` }}
      onClick={() => navegar(destino)}
    >
      <td>{formatearPeriodoCorto(lectura.periodo)}</td>
      <td>{nombreCortoDeTorre(lectura.nombre_torre)}</td>
      <td>
        <Link
          to={destino}
          className="historico-fila__apartamento"
          aria-label={`Apartamento ${lectura.numero_apartamento}, ${lectura.nombre_torre}, ${presentacion.nombreVisible}, ${formatearPeriodoCorto(lectura.periodo)}: ver detalle`}
          onClick={(evento) => evento.stopPropagation()}
        >
          {lectura.numero_apartamento}
        </Link>
      </td>
      <td>
        <span className="historico-servicio">
          <span className="punto" style={{ background: presentacion.variableColor }} />
          {presentacion.nombreVisible}
        </span>
      </td>
      <td className="historico-celda-numero historico-celda-numero--secundaria">
        {formatearLecturaMedidor(lectura.lectura_acumulada, lectura.codigo_servicio)}
      </td>
      <td className="historico-celda-numero">
        {lectura.consumo_periodo === null ? (
          <span className="historico-sin-dato" title={MOTIVO_SIN_DATO} tabIndex={0} aria-label={`Sin dato. ${MOTIVO_SIN_DATO}`}>
            sin dato
          </span>
        ) : (
          formatearConsumo(lectura.consumo_periodo, lectura.codigo_servicio)
        )}
      </td>
      <td className="historico-celda-numero historico-celda-numero--secundaria">
        {lectura.promedio_referencia === null ? '—' : formatearPromedio(lectura.promedio_referencia, lectura.codigo_servicio)}
      </td>
      <td>
        <CeldaEstado lectura={lectura} umbralPorServicio={umbralPorServicio} />
      </td>
    </tr>
  )
}

export function PaginaHistorico() {
  const { cliente } = useSesion()
  const [parametros, establecerParametros] = useSearchParams()
  const textoParametros = parametros.toString()
  const filtros = useMemo(() => leerFiltrosDeUrl(new URLSearchParams(textoParametros)), [textoParametros])
  const clave = claveDeConsulta(filtros)
  const rangoInvertido = rangoDePeriodosInvertido(filtros)

  const [catalogos, establecerCatalogos] = useState<Catalogos>({ torres: [], servicios: [] })
  const [respuesta, establecerRespuesta] = useState<RespuestaConsulta | null>(null)
  const [intento, establecerIntento] = useState(0)
  const [textoApartamento, establecerTextoApartamento] = useState(filtros.apartamento)
  const [apartamentoPrevioEnUrl, establecerApartamentoPrevioEnUrl] = useState(filtros.apartamento)
  const encabezadoResultados = useRef<HTMLDivElement>(null)

  if (filtros.apartamento !== apartamentoPrevioEnUrl) {
    establecerApartamentoPrevioEnUrl(filtros.apartamento)
    if (textoApartamento.trim() !== filtros.apartamento) {
      establecerTextoApartamento(filtros.apartamento)
    }
  }

  const actualizarFiltros = useCallback(
    (cambios: CambiosDeFiltros) => {
      establecerParametros(escribirFiltrosEnUrl({ ...filtros, ...cambios, pagina: 1 }), { replace: true })
    },
    [establecerParametros, filtros],
  )

  useEffect(() => {
    let vigente = true
    Promise.all([cliente.listarTorres(), cliente.listarServicios()])
      .then(([torres, servicios]) => {
        if (vigente) {
          establecerCatalogos({ torres, servicios })
        }
      })
      .catch(() => undefined)
    return () => {
      vigente = false
    }
  }, [cliente])

  useEffect(() => {
    const textoNormalizado = textoApartamento.trim()
    if (textoNormalizado === filtros.apartamento) {
      return undefined
    }
    const temporizador = window.setTimeout(
      () => actualizarFiltros({ apartamento: textoNormalizado }),
      ESPERA_APARTAMENTO_MILISEGUNDOS,
    )
    return () => window.clearTimeout(temporizador)
  }, [textoApartamento, filtros.apartamento, actualizarFiltros])

  useEffect(() => {
    if (rangoInvertido) {
      return undefined
    }
    let vigente = true
    cliente
      .consultarHistorico(convertirEnFiltrosDeApi(filtros))
      .then((pagina) => {
        if (vigente) {
          establecerRespuesta({ clave, estado: 'lista', pagina })
        }
      })
      .catch((error: unknown) => {
        if (vigente && !(error instanceof ErrorSesionVencida)) {
          establecerRespuesta({ clave, estado: 'error', pagina: null })
        }
      })
    return () => {
      vigente = false
    }
  }, [cliente, clave, filtros, rangoInvertido, intento])

  const umbralPorServicio = useMemo(
    () => new Map(catalogos.servicios.map((servicio) => [servicio.codigo, servicio.umbral_desviacion])),
    [catalogos.servicios],
  )

  const cargando = !rangoInvertido && respuesta?.clave !== clave
  const paginaMostrada = respuesta?.pagina ?? null
  const huboError = !cargando && respuesta?.estado === 'error'

  function cambiarPagina(pagina: number) {
    establecerParametros(escribirFiltrosEnUrl({ ...filtros, pagina }))
    encabezadoResultados.current?.scrollIntoView({
      behavior: prefiereMovimientoReducido() ? 'auto' : 'smooth',
      block: 'start',
    })
  }

  function limpiarFiltros() {
    establecerTextoApartamento('')
    establecerParametros(new URLSearchParams(), { replace: true })
  }

  const totalResultados = paginaMostrada?.total_resultados ?? 0
  const totalPaginas = Math.max(1, paginaMostrada?.total_paginas ?? 1)

  return (
    <div className="historico">
      <section className="historico-heroe">
        <div className="historico-heroe__fondo anim-acercamiento">
          <img src={rutaMedio('water-meter-close-up.jpg')} alt="" className="historico-heroe__foto" />
        </div>
        <div className="historico-heroe__degradado" />
        <div className="historico-heroe__contenido">
          <p className="etiqueta-mono historico-heroe__etiqueta historico-ascenso-1">Consulta</p>
          <h1 className="historico-heroe__titular historico-ascenso-2">
            Histórico
            <br />
            de lecturas
          </h1>
        </div>
      </section>

      <section className="historico-seccion-filtros">
        <form className="historico-filtros" role="search" aria-label="Filtros del histórico" onSubmit={(evento) => evento.preventDefault()}>
          <div className="historico-campo">
            <label htmlFor="filtro-torre">Torre</label>
            <select
              id="filtro-torre"
              className="historico-control"
              value={filtros.torre}
              onChange={(evento) => actualizarFiltros({ torre: evento.target.value })}
            >
              <option value="">Todas</option>
              {catalogos.torres.map((torre) => (
                <option key={torre.codigo} value={torre.codigo}>
                  {torre.nombre}
                </option>
              ))}
              {filtros.torre !== '' && !catalogos.torres.some((torre) => torre.codigo === filtros.torre) && (
                <option value={filtros.torre}>{filtros.torre}</option>
              )}
            </select>
          </div>
          <div className="historico-campo">
            <label htmlFor="filtro-servicio">Servicio</label>
            <select
              id="filtro-servicio"
              className="historico-control"
              value={filtros.servicio}
              onChange={(evento) => actualizarFiltros({ servicio: evento.target.value })}
            >
              <option value="">Todos</option>
              {catalogos.servicios.map((servicio) => (
                <option key={servicio.codigo} value={servicio.codigo}>
                  {presentarServicio(servicio.codigo).nombreVisible}
                </option>
              ))}
            </select>
          </div>
          <div className="historico-campo">
            <label htmlFor="filtro-apartamento">Apartamento</label>
            <input
              id="filtro-apartamento"
              className="historico-control"
              type="text"
              inputMode="numeric"
              maxLength={10}
              placeholder="Ej. 502"
              autoComplete="off"
              value={textoApartamento}
              onChange={(evento) => establecerTextoApartamento(evento.target.value)}
            />
          </div>
          <div className="historico-campo">
            <label htmlFor="filtro-desde">Periodo desde</label>
            <input
              id="filtro-desde"
              className="historico-control"
              type="month"
              value={filtros.periodoDesde}
              max={filtros.periodoHasta || undefined}
              onChange={(evento) => actualizarFiltros({ periodoDesde: evento.target.value })}
            />
          </div>
          <div className="historico-campo">
            <label htmlFor="filtro-hasta">Periodo hasta</label>
            <input
              id="filtro-hasta"
              className="historico-control"
              type="month"
              value={filtros.periodoHasta}
              min={filtros.periodoDesde || undefined}
              onChange={(evento) => actualizarFiltros({ periodoHasta: evento.target.value })}
            />
          </div>
          <InterruptorSoloAnomalos
            activo={filtros.soloAnomalos}
            alCambiar={() => actualizarFiltros({ soloAnomalos: !filtros.soloAnomalos })}
          />
        </form>
      </section>

      <section className="historico-seccion-resultados">
        <div className="historico-resumen" ref={encabezadoResultados}>
          <span aria-live="polite">
            {rangoInvertido ? (
              'Revisa el rango de periodos'
            ) : paginaMostrada === null ? (
              'Cargando lecturas…'
            ) : (
              <>
                <strong>{formatearNumero(totalResultados, 0)}</strong>{' '}
                {pluralizar(totalResultados, 'resultado', 'resultados')} · más recientes primero
              </>
            )}
          </span>
          {paginaMostrada !== null && !rangoInvertido && (
            <span>
              Página {Math.min(filtros.pagina, totalPaginas)} de {totalPaginas}
            </span>
          )}
        </div>

        {rangoInvertido && (
          <p role="alert" className="historico-aviso">
            El periodo desde es posterior al periodo hasta. Corrige uno de los dos para ver resultados.
          </p>
        )}

        {huboError && (
          <div role="alert" className="historico-aviso historico-aviso--error">
            <span>No pudimos cargar las lecturas.</span>
            <button
              type="button"
              className="historico-boton-secundario"
              onClick={() => {
                establecerRespuesta(null)
                establecerIntento((actual) => actual + 1)
              }}
            >
              Reintentar
            </button>
          </div>
        )}

        {!rangoInvertido && !huboError && (
          <div className={cargando ? 'historico-tabla-contenedor historico-tabla-contenedor--cargando' : 'historico-tabla-contenedor'} aria-busy={cargando}>
            <table className="historico-tabla">
              <caption className="visualmente-oculto">Lecturas de los medidores, de la más reciente a la más antigua</caption>
              <thead>
                <tr>
                  <th scope="col">Periodo</th>
                  <th scope="col">Torre</th>
                  <th scope="col">Apto</th>
                  <th scope="col">Servicio</th>
                  <th scope="col" className="historico-celda-numero">Lectura medidor</th>
                  <th scope="col" className="historico-celda-numero">Consumo</th>
                  <th scope="col" className="historico-celda-numero">Promedio ref.</th>
                  <th scope="col">Estado</th>
                </tr>
              </thead>
              <tbody>
                {paginaMostrada !== null && paginaMostrada.lecturas.length === 0 && (
                  <tr>
                    <td colSpan={8} className="historico-vacio">
                      {filtros.pagina > totalPaginas && totalResultados > 0
                        ? 'Esta página ya no existe con los filtros actuales.'
                        : 'Ninguna lectura coincide con estos filtros.'}{' '}
                      {filtros.pagina > totalPaginas && totalResultados > 0 ? (
                        <button type="button" className="historico-boton-enlace" onClick={() => cambiarPagina(1)}>
                          Ir a la primera página
                        </button>
                      ) : (
                        hayFiltrosActivos(filtros) && (
                          <button type="button" className="historico-boton-enlace" onClick={limpiarFiltros}>
                            Quitar los filtros
                          </button>
                        )
                      )}
                    </td>
                  </tr>
                )}
                {paginaMostrada?.lecturas.map((lectura, indice) => (
                  <FilaLectura key={lectura.id_lectura} lectura={lectura} indice={indice} umbralPorServicio={umbralPorServicio} />
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="historico-nota">
          “Sin dato”: la lectura es línea base (primera del medidor) o hay un periodo faltante antes de ella, así que no se
          puede calcular el consumo. Pasa el cursor para ver el motivo.
        </p>

        {paginaMostrada !== null && !rangoInvertido && !huboError && (
          <Paginacion
            etiqueta="Páginas del histórico"
            paginaActual={Math.min(filtros.pagina, totalPaginas)}
            totalPaginas={totalPaginas}
            alCambiarPagina={cambiarPagina}
          />
        )}
      </section>
    </div>
  )
}
