import type { CSSProperties } from 'react'
import type { CodigoServicio } from '../../api/tipos'
import { calcularMaximoDeEscala, porcentajeEnEscala } from '../../dominio/escala'
import {
  formatearConsumo,
  formatearNumero,
  formatearPeriodoCorto,
  formatearPeriodoLargo,
  formatearRango,
  presentarServicio,
} from '../../dominio/formato'
import type { PuntoDelHistorial, SituacionEvaluacion } from './datosDetalle'

interface PropiedadesGraficoHistorial {
  puntos: PuntoDelHistorial[]
  situacion: SituacionEvaluacion
  codigoServicio: CodigoServicio
}

const ANCHO_POR_INTERVALO = 100
const ALTO_DEL_LIENZO = 100
const RETRASO_INICIAL_PUNTOS_SEGUNDOS = 0.4
const RETRASO_ENTRE_PUNTOS_SEGUNDOS = 0.18

interface Trazo {
  puntos: PuntoDelHistorial[]
}

function construirTrazos(puntos: PuntoDelHistorial[], excluirUltimoTramo: boolean): Trazo[] {
  const trazos: Trazo[] = []
  let actual: PuntoDelHistorial[] = []
  puntos.forEach((punto, posicion) => {
    const anterior = puntos[posicion - 1]
    const conectaConAnterior =
      anterior !== undefined && anterior.consumo !== null && punto.consumo !== null && !(excluirUltimoTramo && punto.esActual)
    if (!conectaConAnterior) {
      if (actual.length > 1) {
        trazos.push({ puntos: actual })
      }
      actual = punto.consumo === null || (excluirUltimoTramo && punto.esActual) ? [] : [punto]
      return
    }
    actual.push(punto)
  })
  if (actual.length > 1) {
    trazos.push({ puntos: actual })
  }
  return trazos
}

function aTextoSvg(valor: number): string {
  return valor.toFixed(2)
}

function formatearCallout(situacion: SituacionEvaluacion, consumo: number): string | null {
  if (situacion.tipo !== 'evaluada') {
    return null
  }
  if (!situacion.esAnomalo) {
    return 'dentro de lo habitual'
  }
  if (situacion.desviacion >= 0) {
    return `${formatearNumero(consumo / situacion.promedio, 1)} veces lo habitual`
  }
  return `un ${Math.round(Math.abs(situacion.desviacion) * 100)} % menos de lo habitual`
}

export function GraficoHistorial({ puntos, situacion, codigoServicio }: PropiedadesGraficoHistorial) {
  const presentacion = presentarServicio(codigoServicio)
  const ultimoIndice = Math.max(1, puntos.length - 1)
  const consumos = puntos.flatMap((punto) => (punto.consumo === null ? [] : [punto.consumo]))
  const maximo = calcularMaximoDeEscala(situacion.tipo === 'evaluada' ? [...consumos, situacion.limiteSuperior] : consumos)
  const puntoActual = puntos.find((punto) => punto.esActual)
  const actualAnomalo = situacion.tipo === 'evaluada' && situacion.esAnomalo
  const coordenadaX = (punto: PuntoDelHistorial) => punto.indice * ANCHO_POR_INTERVALO
  const coordenadaY = (valor: number) => ALTO_DEL_LIENZO - porcentajeEnEscala(valor, maximo)
  const izquierda = (punto: PuntoDelHistorial) => `${((punto.indice / ultimoIndice) * 100).toFixed(2)}%`
  const abajo = (valor: number) => `${porcentajeEnEscala(valor, maximo).toFixed(2)}%`

  const trazos = construirTrazos(puntos, actualAnomalo)
  const rutaLinea = trazos
    .map((trazo) =>
      trazo.puntos
        .map((punto, posicion) => `${posicion === 0 ? 'M' : 'L'}${coordenadaX(punto)},${aTextoSvg(coordenadaY(punto.consumo ?? 0))}`)
        .join(' '),
    )
    .join(' ')
  const rutaArea = trazos
    .map((trazo) => {
      const primero = trazo.puntos[0]
      const ultimo = trazo.puntos[trazo.puntos.length - 1]
      if (primero === undefined || ultimo === undefined) {
        return ''
      }
      const recorrido = trazo.puntos
        .map((punto, posicion) => `${posicion === 0 ? 'M' : 'L'}${coordenadaX(punto)},${aTextoSvg(coordenadaY(punto.consumo ?? 0))}`)
        .join(' ')
      return `${recorrido} L${coordenadaX(ultimo)},${ALTO_DEL_LIENZO} L${coordenadaX(primero)},${ALTO_DEL_LIENZO} Z`
    })
    .join(' ')
  const puntoPrevioAlActual = puntoActual === undefined ? undefined : puntos[puntoActual.indice - 1]
  const rutaPico =
    actualAnomalo && puntoActual?.consumo != null && puntoPrevioAlActual?.consumo != null
      ? `M${coordenadaX(puntoPrevioAlActual)},${aTextoSvg(coordenadaY(puntoPrevioAlActual.consumo))} L${coordenadaX(puntoActual)},${aTextoSvg(coordenadaY(puntoActual.consumo))}`
      : null
  const puntosIntermedios = puntos.filter((punto) => !punto.esActual && punto.consumo !== null)
  const marcadoresSinConsumo = puntos.filter((punto) => punto.existeLectura && punto.consumo === null)
  const callout = puntoActual?.consumo == null ? null : formatearCallout(situacion, puntoActual.consumo)
  const idDegradado = `area-${codigoServicio.toLowerCase()}`
  const estiloColorServicio = { '--color-servicio': presentacion.variableColor } as CSSProperties

  return (
    <>
      <div className="grafico-historial__desplazable" style={estiloColorServicio}>
        <div className="grafico-historial" aria-hidden="true">
          <div className="grafico-historial__area">
            {situacion.tipo === 'evaluada' && (
              <>
                <div
                  className="grafico-historial__bruma"
                  style={{
                    bottom: abajo(situacion.limiteInferior),
                    height: `${(porcentajeEnEscala(situacion.limiteSuperior, maximo) - porcentajeEnEscala(situacion.limiteInferior, maximo)).toFixed(2)}%`,
                  }}
                />
                <span className="grafico-historial__etiqueta-rango" style={{ bottom: `calc(${abajo(situacion.limiteSuperior)} + 8px)` }}>
                  rango normal · {formatearRango(situacion.limiteInferior, situacion.limiteSuperior, codigoServicio)}
                </span>
                <div className="grafico-historial__promedio" style={{ bottom: abajo(situacion.promedio) }} />
              </>
            )}

            <svg
              className="grafico-historial__lienzo"
              viewBox={`0 0 ${ultimoIndice * ANCHO_POR_INTERVALO} ${ALTO_DEL_LIENZO}`}
              preserveAspectRatio="none"
            >
              <defs>
                <linearGradient id={idDegradado} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" style={{ stopColor: 'var(--color-servicio)', stopOpacity: 0.28 }} />
                  <stop offset="1" style={{ stopColor: 'var(--color-servicio)', stopOpacity: 0 }} />
                </linearGradient>
              </defs>
              {rutaArea !== '' && <path className="grafico-historial__relleno" d={rutaArea} fill={`url(#${idDegradado})`} />}
              {rutaLinea !== '' && (
                <path
                  className="grafico-historial__linea"
                  d={rutaLinea}
                  pathLength={1}
                  fill="none"
                  strokeWidth="2"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                />
              )}
              {rutaPico !== null && (
                <path
                  className="grafico-historial__pico"
                  d={rutaPico}
                  pathLength={1}
                  fill="none"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                />
              )}
            </svg>

            {puntosIntermedios.map((punto, orden) => (
              <div
                key={punto.periodo}
                className="grafico-historial__punto"
                style={{
                  left: izquierda(punto),
                  bottom: abajo(punto.consumo ?? 0),
                  animationDelay: `${(RETRASO_INICIAL_PUNTOS_SEGUNDOS + orden * RETRASO_ENTRE_PUNTOS_SEGUNDOS).toFixed(2)}s`,
                }}
              >
                <span className={punto.esAnomalo ? 'grafico-historial__nucleo grafico-historial__nucleo--anomalo' : 'grafico-historial__nucleo'} />
                <span className="grafico-historial__globo">
                  {formatearPeriodoLargo(punto.periodo)} · {formatearConsumo(punto.consumo ?? 0, codigoServicio)}
                </span>
              </div>
            ))}

            {puntoActual?.consumo != null && (
              <>
                <div className="grafico-historial__cima" style={{ left: izquierda(puntoActual), bottom: abajo(puntoActual.consumo) }}>
                  <span className={actualAnomalo ? 'grafico-historial__punto-actual pulso-anomalia' : 'grafico-historial__punto-actual grafico-historial__punto-actual--normal'} />
                </div>
                <div className="grafico-historial__llamada" style={{ bottom: abajo(puntoActual.consumo) }}>
                  <div className={actualAnomalo ? 'grafico-historial__llamada-valor grafico-historial__llamada-valor--anomalo' : 'grafico-historial__llamada-valor'}>
                    {formatearConsumo(puntoActual.consumo, codigoServicio)}
                  </div>
                  {callout !== null && <div className="grafico-historial__llamada-texto">{callout}</div>}
                </div>
              </>
            )}

            {marcadoresSinConsumo.map((punto) => (
              <div key={punto.periodo} className="grafico-historial__sin-consumo" style={{ left: izquierda(punto) }}>
                <span className="grafico-historial__circulo-punteado" />
                <span
                  className="grafico-historial__etiqueta-sin-consumo"
                  style={{ transform: `translateX(${punto.indice > ultimoIndice * 0.7 ? '-85%' : '-30%'})` }}
                >
                  {punto.esLineaBase || (punto.esActual && situacion.tipo === 'linea_base') ? 'línea base, sin consumo' : 'sin dato'}
                </span>
              </div>
            ))}
          </div>

          <div className="grafico-historial__meses">
            {puntos.map((punto) => (
              <span
                key={punto.periodo}
                className={
                  punto.esActual
                    ? actualAnomalo
                      ? 'grafico-historial__mes grafico-historial__mes--anomalo'
                      : 'grafico-historial__mes grafico-historial__mes--actual'
                    : 'grafico-historial__mes'
                }
                style={{ left: izquierda(punto) }}
              >
                {formatearPeriodoCorto(punto.periodo).slice(0, 3)}
              </span>
            ))}
          </div>
        </div>
      </div>

      <table className="visualmente-oculto">
        <caption>Consumo de los últimos {puntos.length} periodos</caption>
        <thead>
          <tr>
            <th scope="col">Periodo</th>
            <th scope="col">Consumo</th>
            <th scope="col">Estado</th>
          </tr>
        </thead>
        <tbody>
          {puntos.map((punto) => (
            <tr key={punto.periodo}>
              <th scope="row">{formatearPeriodoLargo(punto.periodo)}</th>
              <td>{punto.consumo === null ? (punto.existeLectura ? 'sin dato' : 'sin lectura') : formatearConsumo(punto.consumo, codigoServicio)}</td>
              <td>{punto.esAnomalo ? 'anómalo' : punto.existeLectura ? 'registrado' : 'sin lectura'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
