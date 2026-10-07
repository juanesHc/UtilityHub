import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { ErrorSesionVencida } from '../../api/errores'
import type { Carga, Torre } from '../../api/tipos'
import { PastillaEstadoCarga } from '../../componentes/PastillaEstadoCarga'
import {
  formatearFechaHora,
  formatearNumero,
  formatearPeriodoCorto,
  nombreCortoDeTorre,
  pluralizar,
  presentarEstadoCarga,
} from '../../dominio/formato'
import { rutaMedio } from '../../dominio/medios'
import { useSesion } from '../../sesion/contextoSesion'
import {
  contarPorEstado,
  escribirFiltrosCargas,
  ESTADOS_EN_ORDEN,
  filtrarCargas,
  filtrarPorTorre,
  leerFiltrosCargas,
  tieneProblemas,
  type FiltrosCargas,
} from './filtrosCargas'
import './cargas.css'

type EstadoDatos = { tipo: 'cargando' } | { tipo: 'listo'; cargas: Carga[]; torres: Torre[] } | { tipo: 'error' }

const RETRASO_POR_FILA_SEGUNDOS = 0.04
const MOTIVO_REEMPLAZADA =
  'Sus lecturas se borraron cuando se reprocesó el archivo de esta torre y periodo. Las filas rechazadas se conservan.'

function porcentaje(parte: number, total: number): string {
  return `${((parte / (total || 1)) * 100).toFixed(1)}%`
}

function FilaCarga({ carga, indice }: { carga: Carga; indice: number }) {
  const navegar = useNavigate()
  const destino = `/cargas/${carga.id_carga}`
  const totalFilas = carga.filas_aceptadas + carga.filas_rechazadas
  const reemplazada = carga.estado === 'reemplazada'

  return (
    <tr
      className="cargas-fila"
      style={{ animationDelay: `${(indice * RETRASO_POR_FILA_SEGUNDOS).toFixed(2)}s` }}
      onClick={() => navegar(destino)}
    >
      <td>{formatearPeriodoCorto(carga.periodo)}</td>
      <td>{nombreCortoDeTorre(carga.nombre_torre)}</td>
      <td>
        <Link to={destino} className="cargas-fila__archivo" onClick={(evento) => evento.stopPropagation()}>
          {carga.nombre_archivo}
        </Link>
      </td>
      <td className="cargas-fila__fecha">{formatearFechaHora(carga.fecha_procesamiento)}</td>
      <td>
        <PastillaEstadoCarga estado={carga.estado} />
      </td>
      <td className="cargas-celda-numero">
        {reemplazada ? (
          <span className="cargas-reemplazada" title={MOTIVO_REEMPLAZADA} tabIndex={0} aria-label={`0 aceptadas. ${MOTIVO_REEMPLAZADA}`}>
            0<sup aria-hidden="true">*</sup>
          </span>
        ) : (
          carga.filas_aceptadas
        )}
      </td>
      <td className={carga.filas_rechazadas > 0 ? 'cargas-celda-numero cargas-celda-numero--rechazadas' : 'cargas-celda-numero cargas-celda-numero--sin-rechazos'}>
        {carga.filas_rechazadas}
      </td>
      <td className="cargas-celda-barra">
        <span className="cargas-barra" role="img" aria-label={`${carga.filas_aceptadas} aceptadas y ${carga.filas_rechazadas} rechazadas`}>
          <span style={{ width: porcentaje(carga.filas_aceptadas, totalFilas) }}>
            <span className="cargas-barra__relleno cargas-barra__relleno--aceptadas" />
          </span>
          <span style={{ width: porcentaje(carga.filas_rechazadas, totalFilas) }}>
            <span className="cargas-barra__relleno cargas-barra__relleno--rechazadas" />
          </span>
        </span>
      </td>
    </tr>
  )
}

export function PaginaCargas() {
  const { cliente } = useSesion()
  const [parametros, establecerParametros] = useSearchParams()
  const textoParametros = parametros.toString()
  const filtros = useMemo(() => leerFiltrosCargas(new URLSearchParams(textoParametros)), [textoParametros])
  const [estado, establecerEstado] = useState<EstadoDatos>({ tipo: 'cargando' })
  const [intento, establecerIntento] = useState(0)

  useEffect(() => {
    let vigente = true
    Promise.all([cliente.listarCargas(), cliente.listarTorres()])
      .then(([cargas, torres]) => {
        if (vigente) {
          establecerEstado({ tipo: 'listo', cargas, torres })
        }
      })
      .catch((error: unknown) => {
        if (vigente && !(error instanceof ErrorSesionVencida)) {
          establecerEstado({ tipo: 'error' })
        }
      })
    return () => {
      vigente = false
    }
  }, [cliente, intento])

  function actualizarFiltros(cambios: Partial<FiltrosCargas>) {
    establecerParametros(escribirFiltrosCargas({ ...filtros, ...cambios }), { replace: true })
  }

  const cargas = estado.tipo === 'listo' ? estado.cargas : []
  const torres = estado.tipo === 'listo' ? estado.torres : []
  const deLaTorre = filtrarPorTorre(cargas, filtros.torre)
  const visibles = filtrarCargas(cargas, filtros)
  const conteoPorEstado = contarPorEstado(deLaTorre)
  const conProblemas = cargas.filter(tieneProblemas).length
  const filasRechazadas = cargas
    .filter((carga) => carga.estado !== 'reemplazada')
    .reduce((suma, carga) => suma + carga.filas_rechazadas, 0)
  const hayReemplazadasVisibles = visibles.some((carga) => carga.estado === 'reemplazada')

  return (
    <div className="cargas">
      <section className="cargas-heroe">
        <div className="cargas-heroe__fondo anim-acercamiento">
          <img src={rutaMedio('water-meters.jpg')} alt="" className="cargas-heroe__foto" />
        </div>
        <div className="cargas-heroe__degradado" />
        <div className="cargas-heroe__contenido">
          <div className="cargas-heroe__texto">
            <p className="etiqueta-mono cargas-heroe__etiqueta cargas-ascenso-1">Registro de archivos</p>
            <h1 className="cargas-heroe__titular cargas-ascenso-2">
              Cargas
              <br />
              de lecturas
            </h1>
          </div>
          {estado.tipo === 'listo' && (
            <div className="cargas-heroe__cifras cargas-ascenso-3">
              <div>
                <div className="cargas-cifra">{formatearNumero(cargas.length, 0)}</div>
                <div className="cargas-cifra__descripcion">{pluralizar(cargas.length, 'archivo procesado', 'archivos procesados')}</div>
              </div>
              <div>
                <div className="cargas-cifra cargas-cifra--problema">{conProblemas}</div>
                <div className="cargas-cifra__descripcion">con problemas</div>
              </div>
              <div>
                <div className="cargas-cifra cargas-cifra--anomalia">{formatearNumero(filasRechazadas, 0)}</div>
                <div className="cargas-cifra__descripcion">{pluralizar(filasRechazadas, 'fila rechazada', 'filas rechazadas')}</div>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="cargas-seccion-filtros">
        <form className="cargas-filtros" aria-label="Filtros de cargas" onSubmit={(evento) => evento.preventDefault()}>
          <div className="cargas-campo">
            <label htmlFor="filtro-torre-cargas">Torre</label>
            <select
              id="filtro-torre-cargas"
              className="cargas-control"
              value={filtros.torre}
              onChange={(evento) => actualizarFiltros({ torre: evento.target.value })}
            >
              <option value="">Todas</option>
              {torres.map((torre) => (
                <option key={torre.codigo} value={torre.codigo}>
                  {torre.nombre}
                </option>
              ))}
            </select>
          </div>
          <fieldset className="cargas-estados">
            <legend>Estado</legend>
            <div className="cargas-estados__opciones">
              <button
                type="button"
                className="cargas-estados__opcion"
                aria-pressed={filtros.estado === ''}
                onClick={() => actualizarFiltros({ estado: '' })}
              >
                Todos <span className="cargas-estados__conteo">{deLaTorre.length}</span>
              </button>
              {ESTADOS_EN_ORDEN.map((estadoCarga) => {
                const presentacion = presentarEstadoCarga(estadoCarga)
                return (
                  <button
                    key={estadoCarga}
                    type="button"
                    className="cargas-estados__opcion"
                    aria-pressed={filtros.estado === estadoCarga}
                    onClick={() => actualizarFiltros({ estado: filtros.estado === estadoCarga ? '' : estadoCarga })}
                  >
                    <span className="cargas-estados__punto" style={{ background: presentacion.colorPunto }} aria-hidden="true" />
                    {presentacion.nombreVisible} <span className="cargas-estados__conteo">{conteoPorEstado[estadoCarga]}</span>
                  </button>
                )
              })}
            </div>
          </fieldset>
        </form>
      </section>

      <section className="cargas-seccion-resultados">
        <div className="cargas-resumen" aria-live="polite">
          {estado.tipo === 'cargando' ? (
            'Cargando el registro…'
          ) : estado.tipo === 'listo' ? (
            <span>
              <strong>{visibles.length}</strong> {pluralizar(visibles.length, 'carga', 'cargas')} · más recientes primero
            </span>
          ) : null}
        </div>

        {estado.tipo === 'error' && (
          <div role="alert" className="cargas-aviso">
            <span>No pudimos cargar el registro de cargas.</span>
            <button
              type="button"
              className="cargas-boton-secundario"
              onClick={() => {
                establecerEstado({ tipo: 'cargando' })
                establecerIntento((actual) => actual + 1)
              }}
            >
              Reintentar
            </button>
          </div>
        )}

        {estado.tipo !== 'error' && (
          <div className="cargas-tabla-contenedor" aria-busy={estado.tipo === 'cargando'}>
            <table className="cargas-tabla">
              <caption className="visualmente-oculto">Archivos de lecturas procesados, del más reciente al más antiguo</caption>
              <thead>
                <tr>
                  <th scope="col">Periodo</th>
                  <th scope="col">Torre</th>
                  <th scope="col">Archivo</th>
                  <th scope="col">Procesada</th>
                  <th scope="col">Estado</th>
                  <th scope="col" className="cargas-celda-numero">Aceptadas</th>
                  <th scope="col" className="cargas-celda-numero">Rechazadas</th>
                  <th scope="col">
                    <span className="visualmente-oculto">Proporción de filas aceptadas y rechazadas</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {estado.tipo === 'listo' && visibles.length === 0 && (
                  <tr>
                    <td colSpan={8} className="cargas-vacio">
                      {cargas.length === 0 ? 'Todavía no se ha procesado ningún archivo.' : 'Ninguna carga coincide con estos filtros.'}{' '}
                      {cargas.length > 0 && (
                        <button type="button" className="cargas-boton-enlace" onClick={() => establecerParametros(new URLSearchParams(), { replace: true })}>
                          Quitar los filtros
                        </button>
                      )}
                    </td>
                  </tr>
                )}
                {visibles.map((carga, indice) => (
                  <FilaCarga key={carga.id_carga} carga={carga} indice={indice} />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {hayReemplazadasVisibles && (
          <p className="cargas-nota">
            <sup aria-hidden="true">*</sup> Las cargas reemplazadas muestran 0 aceptadas: sus lecturas se borraron cuando se
            reprocesó el archivo de esa torre y periodo. Sus filas rechazadas se conservan para consulta.
          </p>
        )}
      </section>
    </div>
  )
}
