import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { ErrorSesionVencida } from '../../api/errores'
import type { CodigoServicio } from '../../api/tipos'
import { formatearPeriodoLargo, nombreDelMes, pluralizar, presentarServicio } from '../../dominio/formato'
import { rutaMedio } from '../../dominio/medios'
import { useSesion } from '../../sesion/contextoSesion'
import { cargarResumenInicio, tomarResumenPrecargado, type ResumenInicio, type ResumenServicio } from './resumenInicio'
import { useContadoresAnimados } from './useContadoresAnimados'
import './inicio.css'

type EstadoCargaDatos = { tipo: 'cargando' } | { tipo: 'listo'; resumen: ResumenInicio } | { tipo: 'error' }

const FOTO_POR_SERVICIO: Record<CodigoServicio, { archivo: string; posicion: string }> = {
  AGUA: { archivo: 'clear-water-flowing.jpg', posicion: '50% 55%' },
  ENERGIA: { archivo: 'power-lines-sunset.jpg', posicion: '50% 45%' },
}

function enlaceAlHistorico(periodo: string | null, codigoServicio?: CodigoServicio): string {
  const parametros = new URLSearchParams({ solo_anomalos: 'true' })
  if (codigoServicio !== undefined) {
    parametros.set('servicio', codigoServicio)
  }
  if (periodo !== null) {
    parametros.set('periodo_desde', periodo)
    parametros.set('periodo_hasta', periodo)
  }
  return `/historico?${parametros.toString()}`
}

function FlechaGrande({ tamano }: { tamano: number }) {
  return (
    <svg className="inicio-flecha" width={tamano} height={tamano} viewBox="0 0 24 24" fill="none" stroke="#F2F1EC" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 12h16M13 5l7 7-7 7" />
    </svg>
  )
}

function FilaServicio({ resumen, periodo, cantidadTorres }: { resumen: ResumenServicio; periodo: string | null; cantidadTorres: number }) {
  const presentacion = presentarServicio(resumen.codigoServicio)
  const foto = FOTO_POR_SERVICIO[resumen.codigoServicio]
  const nombreEnMinuscula = presentacion.nombreVisible.toLowerCase()
  const detalleMedicion = resumen.hayConsumosPorDebajo
    ? `Consumo medido en ${presentacion.unidadVisible}, incluye consumos muy por debajo de lo habitual.`
    : `Consumo medido en ${presentacion.unidadVisible} por apartamento, en las ${cantidadTorres} torres.`

  return (
    <Link to={enlaceAlHistorico(periodo, resumen.codigoServicio)} className="inicio-servicio">
      <img className="inicio-foto-al-pasar" src={rutaMedio(foto.archivo)} alt="" style={{ objectPosition: foto.posicion }} />
      <div className="inicio-servicio__contenido">
        <div className="inicio-servicio__resumen">
          <span className="inicio-servicio__punto" style={{ background: presentacion.variableColor }} />
          <span>
            <strong>
              {resumen.cantidadAnomalias === 0
                ? 'Sin anomalías'
                : `${resumen.cantidadAnomalias} ${pluralizar(resumen.cantidadAnomalias, 'anomalía', 'anomalías')}`}
            </strong>{' '}
            en {nombreEnMinuscula} este periodo. {detalleMedicion}
          </span>
        </div>
        <span className="inicio-palabra inicio-servicio__palabra">{presentacion.nombreVisible}</span>
        <FlechaGrande tamano={72} />
      </div>
    </Link>
  )
}

function Encabezado({ resumen, contadores }: { resumen: ResumenInicio | null; contadores: { anomalias: number; problemas: number } }) {
  const total = resumen?.totalAnomalias ?? 0
  const etiquetaPeriodo =
    resumen === null ? 'Preparando el resumen…' : resumen.periodo === null ? 'Sin lecturas todavía' : `Periodo · ${formatearPeriodoLargo(resumen.periodo)}`
  const titular =
    resumen !== null && total === 0 ? (
      <>
        Ningún consumo
        <br />
        fuera de lo normal.
      </>
    ) : (
      <>
        {contadores.anomalias} {pluralizar(total, 'consumo', 'consumos')}
        <br />
        fuera de lo normal.
      </>
    )

  return (
    <section className="inicio-heroe" aria-busy={resumen === null}>
      <div className="inicio-heroe__fondo anim-acercamiento">
        <img src={rutaMedio('residential-towers-sunset.jpg')} alt="" className="inicio-heroe__foto" />
      </div>
      <div className="inicio-heroe__degradado" />
      <div className="inicio-heroe__contenido">
        <div className="inicio-heroe__texto">
          <p className="etiqueta-mono inicio-heroe__etiqueta inicio-ascenso-1">{etiquetaPeriodo}</p>
          <h1 className="inicio-heroe__titular inicio-ascenso-2">{titular}</h1>
        </div>
        <div className="inicio-heroe__cifras inicio-ascenso-3">
          <div>
            <div className="inicio-cifra inicio-cifra--anomalia">{contadores.anomalias}</div>
            <div className="inicio-cifra__descripcion">anomalías del periodo</div>
          </div>
          <div>
            <div className="inicio-cifra inicio-cifra--problema">{contadores.problemas}</div>
            <div className="inicio-cifra__descripcion">cargas con problemas</div>
          </div>
        </div>
      </div>
    </section>
  )
}

function SeccionAtencion({ resumen }: { resumen: ResumenInicio }) {
  const total = resumen.totalAnomalias
  return (
    <section className="inicio-seccion">
      <div className="inicio-seccion__cabecera">
        <h2 className="inicio-seccion__titulo">Requieren tu atención</h2>
        {total > 0 && (
          <Link to={enlaceAlHistorico(resumen.periodo)} className="inicio-seccion__enlace">
            {total === 1 ? 'Verla en el histórico →' : `Ver las ${total} en el histórico →`}
          </Link>
        )}
      </div>
      <div className="inicio-lista">
        {resumen.anomaliasDestacadas.length === 0 ? (
          <p className="inicio-lista__vacia">
            Ningún consumo fuera de lo normal{resumen.periodo === null ? '' : ` en ${nombreDelMes(resumen.periodo)}`}. Todo en orden.
          </p>
        ) : (
          resumen.anomaliasDestacadas.map((anomalia) => {
            const presentacion = presentarServicio(anomalia.codigoServicio)
            return (
              <Link key={anomalia.idLectura} to={`/lecturas/${anomalia.idLectura}`} className="inicio-anomalia">
                <div className="inicio-anomalia__ubicacion">
                  <div className="inicio-anomalia__lugar">
                    {anomalia.nombreTorre} · Apto {anomalia.numeroApartamento}
                  </div>
                  <div className="inicio-anomalia__servicio">
                    <span className="punto" style={{ background: presentacion.variableColor }} />
                    {presentacion.nombreVisible}
                  </div>
                </div>
                <div className="inicio-anomalia__consumo">
                  <span className="inicio-anomalia__valor">{anomalia.consumoTexto}</span> · normal {anomalia.rangoTexto}
                </div>
                <div className="inicio-anomalia__desviacion">{anomalia.desviacionTexto}</div>
                <svg className="inicio-anomalia__ir" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#9AA1A6" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M9 6l6 6-6 6" />
                </svg>
              </Link>
            )
          })
        )}
      </div>
    </section>
  )
}

function SeccionCargas({ resumen }: { resumen: ResumenInicio }) {
  const mes = resumen.periodo === null ? null : nombreDelMes(resumen.periodo)
  return (
    <section className="inicio-seccion inicio-seccion--cargas" id="cargas">
      <div className="inicio-seccion__cabecera inicio-seccion__cabecera--amplia">
        <div>
          <p className="etiqueta-mono inicio-seccion__etiqueta">Últimas cargas</p>
          <h2 className="inicio-cargas__titular">
            Así llegaron los
            <br />
            archivos de {mes ?? 'este periodo'}.
          </h2>
        </div>
        <Link to="/cargas" className="inicio-seccion__enlace">
          Ver todas las cargas →
        </Link>
      </div>
      <div className="inicio-lista">
        {resumen.cargasDelPeriodo.length === 0 ? (
          <p className="inicio-lista__vacia">Todavía no hay archivos de este periodo.</p>
        ) : (
          resumen.cargasDelPeriodo.map((carga) => (
            <Link key={carga.idCarga} to={`/cargas/${carga.idCarga}`} className="inicio-servicio inicio-carga">
              <img className="inicio-foto-al-pasar inicio-carga__foto" src={rutaMedio('water-meters.jpg')} alt="" />
              <div className="inicio-carga__contenido">
                <div className="inicio-carga__torre">
                  <div className="inicio-carga__orden">
                    {carga.numeroOrden} · {carga.periodoCorto}
                  </div>
                  <div className="inicio-carga__nombre">{carga.nombreTorre}</div>
                </div>
                <div className="inicio-carga__detalle">
                  <div className="inicio-palabra inicio-carga__frase" style={{ color: carga.colorFrase }}>
                    {carga.frase}
                  </div>
                  <div className="inicio-carga__barra" role="img" aria-label={`${carga.filasAceptadas} filas aceptadas y ${carga.filasRechazadas} rechazadas`}>
                    <span style={{ width: carga.porcentajeAceptadas }}>
                      <span className="inicio-carga__relleno inicio-carga__relleno--aceptadas" />
                    </span>
                    <span style={{ width: carga.porcentajeRechazadas }}>
                      <span className="inicio-carga__relleno inicio-carga__relleno--rechazadas" />
                    </span>
                  </div>
                  <div className="inicio-carga__conteos">
                    <span>{carga.filasAceptadas} aceptadas</span>
                    <span className={carga.filasRechazadas > 0 ? 'inicio-carga__rechazadas--con-filas' : 'inicio-carga__rechazadas'}>
                      {carga.filasRechazadas} rechazadas
                    </span>
                    <span className="inicio-carga__archivo">{carga.nombreArchivo}</span>
                  </div>
                </div>
                <div className="inicio-carga__estado">
                  <span className="inicio-carga__estado-texto" style={{ color: carga.colorTinta }}>
                    <span className="inicio-carga__estado-punto" style={{ background: carga.colorPunto }} />
                    {carga.estadoVisible}
                  </span>
                  <FlechaGrande tamano={48} />
                </div>
              </div>
            </Link>
          ))
        )}
      </div>
    </section>
  )
}

export function PaginaInicio() {
  const { cliente } = useSesion()
  const [estado, establecerEstado] = useState<EstadoCargaDatos>({ tipo: 'cargando' })
  const [intento, establecerIntento] = useState(0)

  useEffect(() => {
    let vigente = true
    const promesa = (intento === 0 ? tomarResumenPrecargado(cliente) : null) ?? cargarResumenInicio(cliente)
    promesa
      .then((resumen) => {
        if (vigente) {
          establecerEstado({ tipo: 'listo', resumen })
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

  const resumen = estado.tipo === 'listo' ? estado.resumen : null
  const objetivoContadores = useMemo(
    () => (resumen === null ? null : { anomalias: resumen.totalAnomalias, problemas: resumen.cargasConProblemas }),
    [resumen],
  )
  const contadores = useContadoresAnimados(objetivoContadores)

  return (
    <div className="inicio">
      <Encabezado resumen={resumen} contadores={contadores} />

      {estado.tipo === 'error' && (
        <section className="inicio-seccion">
          <div className="inicio-error" role="alert">
            <p>No pudimos cargar el resumen del periodo.</p>
            <button
              type="button"
              className="inicio-error__boton"
              onClick={() => {
                establecerEstado({ tipo: 'cargando' })
                establecerIntento((actual) => actual + 1)
              }}
            >
              Reintentar
            </button>
          </div>
        </section>
      )}

      {resumen !== null && (
        <>
          <section className="inicio-seccion inicio-seccion--servicios">
            <p className="etiqueta-mono inicio-seccion__etiqueta inicio-seccion__etiqueta--compacta">Por servicio</p>
            {resumen.resumenPorServicio.map((resumenServicio) => (
              <FilaServicio
                key={resumenServicio.codigoServicio}
                resumen={resumenServicio}
                periodo={resumen.periodo}
                cantidadTorres={resumen.cantidadTorres}
              />
            ))}
          </section>
          <SeccionAtencion resumen={resumen} />
          <SeccionCargas resumen={resumen} />
        </>
      )}
    </div>
  )
}
