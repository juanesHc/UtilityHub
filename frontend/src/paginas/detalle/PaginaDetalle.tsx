import { useEffect, useState, type CSSProperties } from 'react'
import { Link, useParams } from 'react-router'
import { ErrorRecursoInexistente, ErrorSesionVencida } from '../../api/errores'
import type { Carga, CodigoServicio, DetalleLectura } from '../../api/tipos'
import { EnlaceVolver } from '../../componentes/EnlaceVolver'
import { PastillaEstadoCarga } from '../../componentes/PastillaEstadoCarga'
import { calcularMaximoDeEscala, porcentajeEnEscala } from '../../dominio/escala'
import {
  formatearConsumo,
  formatearDesviacion,
  formatearFechaDeLectura,
  formatearFechaDeProcesamiento,
  formatearNumero,
  formatearPeriodoLargo,
  formatearPromedio,
  nombreDelMes,
  numeroEnPalabras,
  presentarServicio,
} from '../../dominio/formato'
import { rutaMedio } from '../../dominio/medios'
import { useSesion } from '../../sesion/contextoSesion'
import { cargarDetalleCompleto, type DetalleCompleto, type PuntoDelHistorial, type SituacionEvaluacion } from './datosDetalle'
import { GraficoHistorial } from './GraficoHistorial'
import './detalle.css'

type EstadoDetalle =
  | { tipo: 'cargando' }
  | { tipo: 'listo'; datos: DetalleCompleto }
  | { tipo: 'inexistente' }
  | { tipo: 'error' }

interface RespuestaDetalle {
  idLectura: number
  estado: EstadoDetalle
}

function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

function leerIdLectura(texto: string | undefined): number | null {
  const id = Number(texto)
  return Number.isInteger(id) && id > 0 ? id : null
}

function CifraPrincipal({ situacion }: { situacion: SituacionEvaluacion }) {
  if (situacion.tipo !== 'evaluada') {
    return (
      <div className="detalle-heroe__cifra detalle-ascenso-3">
        <div className="detalle-heroe__valor detalle-heroe__valor--sin-evaluar">Sin evaluar</div>
      </div>
    )
  }
  const descripcion = !situacion.esAnomalo
    ? 'respecto al promedio, dentro de lo normal'
    : situacion.desviacion >= 0
      ? 'sobre lo normal para este apartamento'
      : 'por debajo de lo normal para este apartamento'
  return (
    <div className="detalle-heroe__cifra detalle-ascenso-3">
      <div className={situacion.esAnomalo ? 'detalle-heroe__valor detalle-heroe__valor--anomalo' : 'detalle-heroe__valor'}>
        {formatearDesviacion(situacion.desviacion)}
      </div>
      <div className="detalle-heroe__descripcion">{descripcion}</div>
    </div>
  )
}

function Datos({ detalle }: { detalle: DetalleLectura }) {
  const claseConsumo =
    detalle.consumo_periodo === null
      ? 'detalle-datos__valor detalle-datos__valor--mono detalle-datos__valor--apagado'
      : detalle.es_anomalo
        ? 'detalle-datos__valor detalle-datos__valor--mono detalle-datos__valor--anomalo'
        : 'detalle-datos__valor detalle-datos__valor--mono'
  return (
    <section className="detalle-seccion detalle-seccion--datos">
      <dl className="detalle-datos">
        <div className="detalle-datos__celda">
          <dt>Periodo</dt>
          <dd className="detalle-datos__valor">{formatearPeriodoLargo(detalle.periodo)}</dd>
        </div>
        <div className="detalle-datos__celda">
          <dt>Fecha de lectura</dt>
          <dd className="detalle-datos__valor">{formatearFechaDeLectura(detalle.fecha_lectura)}</dd>
        </div>
        <div className="detalle-datos__celda">
          <dt>Lectura acumulada</dt>
          <dd className="detalle-datos__valor detalle-datos__valor--mono">
            {formatearConsumo(detalle.lectura_acumulada, detalle.codigo_servicio)}
          </dd>
        </div>
        <div className="detalle-datos__celda">
          <dt>Consumo del periodo</dt>
          <dd className={claseConsumo}>
            {detalle.consumo_periodo === null ? 'sin dato' : formatearConsumo(detalle.consumo_periodo, detalle.codigo_servicio)}
          </dd>
        </div>
      </dl>
    </section>
  )
}

function BarraDeRango({
  situacion,
  consumo,
  codigoServicio,
}: {
  situacion: Extract<SituacionEvaluacion, { tipo: 'evaluada' }>
  consumo: number
  codigoServicio: CodigoServicio
}) {
  const presentacion = presentarServicio(codigoServicio)
  const maximo = calcularMaximoDeEscala([consumo, situacion.limiteSuperior])
  const inferior = porcentajeEnEscala(situacion.limiteInferior, maximo)
  const superior = porcentajeEnEscala(situacion.limiteSuperior, maximo)
  const promedio = porcentajeEnEscala(situacion.promedio, maximo)
  const posicionConsumo = porcentajeEnEscala(consumo, maximo)
  const estiloMarcador = {
    '--desplazamiento-inicial': `${(promedio - posicionConsumo).toFixed(2)}%`,
  } as CSSProperties
  const estiloServicio = { '--color-servicio': presentacion.variableColor } as CSSProperties

  return (
    <div className="detalle-rango" style={estiloServicio} role="img" aria-label={`Rango normal de ${formatearNumero(situacion.limiteInferior, presentacion.decimales)} a ${formatearNumero(situacion.limiteSuperior, presentacion.decimales)} ${presentacion.unidadVisible}; consumo del periodo ${formatearConsumo(consumo, codigoServicio)}`}>
      <div className="detalle-rango__pista" />
      <div className="detalle-rango__banda" style={{ left: `${inferior}%`, width: `${superior - inferior}%` }} />
      <div className="detalle-rango__promedio" style={{ left: `${promedio}%` }} />
      <div className="detalle-rango__etiqueta-promedio" style={{ left: `${promedio}%` }}>
        promedio {formatearNumero(situacion.promedio, presentacion.decimales === 0 ? 0 : 2)}
      </div>
      <div className="detalle-rango__limite" style={{ left: `${inferior}%` }}>
        {formatearNumero(situacion.limiteInferior, presentacion.decimales)}
      </div>
      <div className="detalle-rango__limite" style={{ left: `${superior}%` }}>
        {formatearNumero(situacion.limiteSuperior, presentacion.decimales)}
      </div>
      <div className="detalle-rango__capa-marcador" style={estiloMarcador}>
        <div className="detalle-rango__marcador" style={{ left: `${posicionConsumo}%` }}>
          <span className={situacion.esAnomalo ? 'detalle-rango__valor detalle-rango__valor--anomalo' : 'detalle-rango__valor'}>
            {formatearConsumo(consumo, codigoServicio)}
          </span>
          <span className={situacion.esAnomalo ? 'detalle-rango__punto pulso-anomalia' : 'detalle-rango__punto detalle-rango__punto--normal'} />
        </div>
      </div>
      <div className="detalle-rango__extremo detalle-rango__extremo--inicio">0</div>
      <div className="detalle-rango__extremo detalle-rango__extremo--fin">
        {formatearNumero(maximo, 0)} {presentacion.unidadVisible}
      </div>
    </div>
  )
}

function Explicacion({ detalle, situacion }: { detalle: DetalleLectura; situacion: SituacionEvaluacion }) {
  const presentacion = presentarServicio(detalle.codigo_servicio)
  const servicioEnMinuscula = presentacion.nombreVisible.toLowerCase()

  if (situacion.tipo === 'evaluada' && detalle.consumo_periodo !== null) {
    return (
      <section className="detalle-seccion detalle-seccion--explicacion">
        <h2 className="detalle-titulo-seccion">
          {situacion.esAnomalo ? 'Por qué se marcó como anómalo' : 'Por qué está dentro de lo normal'}
        </h2>
        <p className="detalle-explicacion">
          El promedio de referencia de este apartamento es{' '}
          <strong>{formatearPromedio(situacion.promedio, detalle.codigo_servicio)}</strong>. Con el umbral del servicio de{' '}
          {servicioEnMinuscula} (<strong>±{Math.round(situacion.umbral * 100)}&nbsp;%</strong>), lo normal está entre{' '}
          <strong>
            {formatearNumero(situacion.limiteInferior, presentacion.decimales)} y{' '}
            {formatearConsumo(situacion.limiteSuperior, detalle.codigo_servicio)}
          </strong>
          . Este mes consumió{' '}
          <strong className={situacion.esAnomalo ? 'detalle-explicacion__anomalo' : undefined}>
            {formatearConsumo(detalle.consumo_periodo, detalle.codigo_servicio)}
          </strong>
          .
        </p>
        <BarraDeRango situacion={situacion} consumo={detalle.consumo_periodo} codigoServicio={detalle.codigo_servicio} />
        <p className="detalle-nota">
          Se muestra el umbral vigente hoy para el servicio de {servicioEnMinuscula}; puede diferir del que se usó cuando se
          procesó la carga.
        </p>
      </section>
    )
  }

  const motivo =
    situacion.tipo === 'linea_base'
      ? 'Es la línea base del medidor: la primera lectura registrada. Sin una lectura anterior no se puede calcular el consumo del periodo, y sin historial no hay promedio con qué compararlo.'
      : situacion.tipo === 'hueco'
        ? `Falta la lectura de ${nombreDelMes(situacion.periodoFaltante)} de ${situacion.periodoFaltante.slice(0, 4)}. Sin ella no se puede calcular el consumo de ${nombreDelMes(detalle.periodo)}: la lectura del medidor quedó guardada, pero el consumo del periodo no tiene con qué restarse.`
        : `Es uno de los primeros periodos del medidor: el consumo ya se calculó, pero todavía no hay consumos anteriores con qué formar un promedio de referencia.`

  return (
    <section className="detalle-seccion detalle-seccion--explicacion">
      <div className="detalle-sin-evaluar">
        <h2 className="detalle-sin-evaluar__titulo">Esta lectura no se evaluó</h2>
        <p className="detalle-sin-evaluar__texto">{motivo}</p>
      </div>
    </section>
  )
}

function TitularHistorial({ puntos, situacion, periodo }: { puntos: PuntoDelHistorial[]; situacion: SituacionEvaluacion; periodo: string }) {
  const anteriores = puntos.filter((punto) => !punto.esActual && punto.existeLectura)
  const cantidadConActual = anteriores.length + 1
  const mes = nombreDelMes(periodo)
  const historial =
    cantidadConActual === 1 ? 'Un periodo de historial.' : `${capitalizar(numeroEnPalabras(cantidadConActual))} periodos de historial.`

  if (situacion.tipo === 'evaluada' && situacion.esAnomalo) {
    const huboAnomaliasAntes = anteriores.some((punto) => punto.esAnomalo)
    const primeraLinea =
      !huboAnomaliasAntes && anteriores.length > 0
        ? anteriores.length === 1
          ? 'Un mes tranquilo.'
          : `${capitalizar(numeroEnPalabras(anteriores.length))} meses tranquilos.`
        : historial
    const segundaLinea = !huboAnomaliasAntes && anteriores.length > 0 ? `Y luego, ${mes}.` : `${capitalizar(mes)} se salió de lo normal.`
    return (
      <h2 className="detalle-titular-historial">
        {primeraLinea}
        <br />
        <span className="detalle-titular-historial__destacado">{segundaLinea}</span>
      </h2>
    )
  }

  return (
    <h2 className="detalle-titular-historial">
      {historial}
      <br />
      <span className="detalle-titular-historial__apagado">
        {situacion.tipo === 'evaluada' ? `${capitalizar(mes)}, dentro de lo esperado.` : `${capitalizar(mes)}, sin evaluar.`}
      </span>
    </h2>
  )
}

function TarjetaCarga({ carga }: { carga: Carga }) {
  return (
    <section className="detalle-seccion detalle-seccion--carga" id="carga-origen">
      <p className="etiqueta-mono detalle-etiqueta-seccion">Carga de origen</p>
      <Link to={`/cargas/${carga.id_carga}`} className="detalle-tarjeta-carga">
        <span className="detalle-tarjeta-carga__texto">
          <span className="detalle-tarjeta-carga__archivo">{carga.nombre_archivo}</span>
          <span className="detalle-tarjeta-carga__resumen">
            {carga.nombre_torre} · procesada {formatearFechaDeProcesamiento(carga.fecha_procesamiento)} · {carga.filas_aceptadas}{' '}
            aceptadas, {carga.filas_rechazadas} rechazadas
          </span>
        </span>
        <span className="detalle-tarjeta-carga__estado">
          <PastillaEstadoCarga estado={carga.estado} conPunto={false} />
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#C9CCCB" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </span>
      </Link>
    </section>
  )
}

function Heroe({ detalle, situacion }: { detalle: DetalleLectura | null; situacion: SituacionEvaluacion | null }) {
  const presentacion = detalle === null ? null : presentarServicio(detalle.codigo_servicio)
  return (
    <section className="detalle-heroe">
      <div className="detalle-heroe__fondo anim-acercamiento">
        <img src={rutaMedio('apartment-building-night-windows.jpg')} alt="" className="detalle-heroe__foto" />
      </div>
      <div className="detalle-heroe__degradado" />
      <div className="detalle-heroe__contenido">
        <div className="detalle-heroe__texto">
          <EnlaceVolver destinoPorDefecto="/historico" texto="Volver al histórico" className="detalle-volver detalle-ascenso-1" />
          {detalle !== null && presentacion !== null ? (
            <>
              <div className="etiqueta-mono detalle-heroe__servicio detalle-ascenso-1" style={{ color: presentacion.variableColor }}>
                <span className="punto" style={{ background: presentacion.variableColor }} />
                {presentacion.nombreVisible} · {formatearPeriodoLargo(detalle.periodo)}
              </div>
              <h1 className="detalle-heroe__titular detalle-ascenso-2">
                {detalle.nombre_torre}
                <br />
                Apto {detalle.numero_apartamento}
              </h1>
            </>
          ) : (
            <h1 className="detalle-heroe__titular detalle-heroe__titular--cargando">Detalle de la lectura</h1>
          )}
        </div>
        {situacion !== null && <CifraPrincipal situacion={situacion} />}
      </div>
    </section>
  )
}

export function PaginaDetalle() {
  const { cliente } = useSesion()
  const { idLectura: textoId } = useParams()
  const idLectura = leerIdLectura(textoId)
  const [respuesta, establecerRespuesta] = useState<RespuestaDetalle | null>(null)
  const [intento, establecerIntento] = useState(0)

  useEffect(() => {
    if (idLectura === null) {
      return undefined
    }
    let vigente = true
    cargarDetalleCompleto(cliente, idLectura)
      .then((datos) => {
        if (vigente) {
          establecerRespuesta({ idLectura, estado: { tipo: 'listo', datos } })
        }
      })
      .catch((error: unknown) => {
        if (!vigente || error instanceof ErrorSesionVencida) {
          return
        }
        establecerRespuesta({ idLectura, estado: error instanceof ErrorRecursoInexistente ? { tipo: 'inexistente' } : { tipo: 'error' } })
      })
    return () => {
      vigente = false
    }
  }, [cliente, idLectura, intento])

  const estado: EstadoDetalle =
    idLectura === null ? { tipo: 'inexistente' } : respuesta?.idLectura === idLectura ? respuesta.estado : { tipo: 'cargando' }
  const datos = estado.tipo === 'listo' ? estado.datos : null

  return (
    <div className="detalle">
      <Heroe detalle={datos?.detalle ?? null} situacion={datos?.situacion ?? null} />

      {estado.tipo === 'cargando' && (
        <section className="detalle-seccion">
          <p className="detalle-estado" aria-live="polite">
            Cargando la lectura…
          </p>
        </section>
      )}

      {estado.tipo === 'inexistente' && (
        <section className="detalle-seccion">
          <div className="detalle-aviso" role="alert">
            <p>Esta lectura no existe o ya no está disponible.</p>
            <Link to="/historico">Ir al histórico</Link>
          </div>
        </section>
      )}

      {estado.tipo === 'error' && (
        <section className="detalle-seccion">
          <div className="detalle-aviso detalle-aviso--error" role="alert">
            <p>No pudimos cargar la lectura.</p>
            <button
              type="button"
              className="detalle-boton-secundario"
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
          <Datos detalle={datos.detalle} />
          <Explicacion detalle={datos.detalle} situacion={datos.situacion} />
          <section className="detalle-seccion detalle-seccion--historial">
            <p className="etiqueta-mono detalle-etiqueta-seccion">
              {datos.puntos.length === 1 ? 'Único periodo registrado' : `Últimos ${datos.puntos.length} periodos`}
            </p>
            <TitularHistorial puntos={datos.puntos} situacion={datos.situacion} periodo={datos.detalle.periodo} />
            <GraficoHistorial puntos={datos.puntos} situacion={datos.situacion} codigoServicio={datos.detalle.codigo_servicio} />
          </section>
          {datos.carga !== null && <TarjetaCarga carga={datos.carga} />}
        </>
      )}
    </div>
  )
}
