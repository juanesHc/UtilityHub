import { useEffect, useState, type FormEvent } from 'react'
import { Navigate, useLocation } from 'react-router'
import { ErrorConexion, ErrorCredencialesInvalidas, ErrorCuentaBloqueada, ErrorSolicitudInvalida } from '../../api/errores'
import { VideoSilencioso } from '../../componentes/VideoSilencioso'
import { pluralizar } from '../../dominio/formato'
import { prefiereMovimientoReducido, rutaMedio } from '../../dominio/medios'
import { precargarResumenInicio } from '../inicio/resumenInicio'
import { sesionVigente } from '../../sesion/almacenSesion'
import { useSesion, type EstadoNavegacionLogin } from '../../sesion/contextoSesion'
import { useTransicionDeNube } from '../../transicion/contextoTransicion'
import './login.css'

type AvisoFormulario =
  | { tipo: 'incorrecto' }
  | { tipo: 'bloqueada'; minutos: number }
  | { tipo: 'vencida' }
  | { tipo: 'conexion' }
  | { tipo: 'inesperado' }

function avisoInicial(estado: unknown): AvisoFormulario | null {
  const estadoLogin = estado as EstadoNavegacionLogin | null
  return estadoLogin?.aviso === 'vencida' ? { tipo: 'vencida' } : null
}

function traducirError(error: unknown): AvisoFormulario {
  if (error instanceof ErrorCredencialesInvalidas || error instanceof ErrorSolicitudInvalida) {
    return { tipo: 'incorrecto' }
  }
  if (error instanceof ErrorCuentaBloqueada) {
    return { tipo: 'bloqueada', minutos: error.minutosRestantes }
  }
  if (error instanceof ErrorConexion) {
    return { tipo: 'conexion' }
  }
  return { tipo: 'inesperado' }
}

function MensajeDeAviso({ aviso }: { aviso: AvisoFormulario }) {
  switch (aviso.tipo) {
    case 'incorrecto':
      return (
        <p role="alert" className="login-aviso login-aviso--error">
          Usuario o clave incorrectos.
        </p>
      )
    case 'bloqueada':
      return (
        <p role="alert" className="login-aviso login-aviso--bloqueo">
          Cuenta bloqueada por intentos fallidos. Intenta de nuevo en {aviso.minutos}{' '}
          {pluralizar(aviso.minutos, 'minuto', 'minutos')}.
        </p>
      )
    case 'vencida':
      return (
        <p role="status" className="login-aviso login-aviso--sesion">
          Tu sesión venció. Vuelve a iniciar sesión para continuar.
        </p>
      )
    case 'conexion':
      return (
        <p role="alert" className="login-aviso login-aviso--error">
          No pudimos conectarnos con el servidor. Revisa tu conexión e inténtalo de nuevo.
        </p>
      )
    case 'inesperado':
      return (
        <p role="alert" className="login-aviso login-aviso--error">
          Ocurrió un error inesperado. Inténtalo de nuevo en unos minutos.
        </p>
      )
  }
}

export function PaginaLogin() {
  const { sesion, cliente, abrirSesion } = useSesion()
  const { etapa, prepararTransicion, iniciarTransicion } = useTransicionDeNube()
  const ubicacion = useLocation()
  const [teniaSesionAlEntrar] = useState(() => sesionVigente(sesion))
  const [usuario, establecerUsuario] = useState('')
  const [clave, establecerClave] = useState('')
  const [enviando, establecerEnviando] = useState(false)
  const [aviso, establecerAviso] = useState<AvisoFormulario | null>(() => avisoInicial(ubicacion.state))
  const [movimientoReducido] = useState(prefiereMovimientoReducido)

  useEffect(() => prepararTransicion(), [prepararTransicion])

  if (teniaSesionAlEntrar) {
    return <Navigate to="/inicio" replace />
  }

  const saliendo = etapa === 'cubriendo'

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (enviando || saliendo) {
      return
    }
    establecerEnviando(true)
    establecerAviso(null)
    try {
      const tokenAcceso = await cliente.iniciarSesion(usuario, clave)
      abrirSesion(tokenAcceso.token_acceso)
      precargarResumenInicio(cliente)
      iniciarTransicion('/inicio')
    } catch (error) {
      establecerAviso(traducirError(error))
      establecerEnviando(false)
    }
  }

  return (
    <div className="login">
      <div className="login__fondo anim-acercamiento">
        {movimientoReducido ? (
          <img className="login__medio" src={rutaMedio('sunset-poster.jpg')} alt="" />
        ) : (
          <VideoSilencioso
            className="login__medio"
            fuente={rutaMedio('sunset-loop.mp4')}
            poster={rutaMedio('sunset-poster.jpg')}
          />
        )}
      </div>
      <div className="login__degradado" />

      <header className="login__encabezado">
        <div className="logo logo--grande">
          Utility<span className="logo__ligero">Hub</span>
        </div>
        <div className="login__lema">Monitoreo de agua y energía · Conjunto residencial</div>
      </header>

      <main className={saliendo ? 'login__principal login__principal--saliendo' : 'login__principal'}>
        <div className="login__presentacion">
          <p className="etiqueta-mono login__etiqueta login-ascenso-1">Panel del administrador</p>
          <h1 className="login__titular">
            <span className="login-ascenso-2">Cada gota.</span>
            <span className="login__titular-luz login-ascenso-3">Cada kilovatio.</span>
          </h1>
          <p className="login__descripcion login-ascenso-3">
            Lecturas de todos los medidores, consumos fuera de lo normal y el estado de cada carga, en un solo lugar.
          </p>
        </div>

        <form className="login__tarjeta" onSubmit={enviar} aria-busy={enviando}>
          <h2 className="login__titulo-tarjeta">Iniciar sesión</h2>

          {aviso !== null && <MensajeDeAviso aviso={aviso} />}

          <div className="login__campo">
            <label htmlFor="usuario">Usuario</label>
            <input
              id="usuario"
              className="login__entrada"
              type="text"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              placeholder="admin.torres"
              required
              value={usuario}
              onChange={(evento) => establecerUsuario(evento.target.value)}
            />
          </div>
          <div className="login__campo">
            <label htmlFor="clave">Clave</label>
            <input
              id="clave"
              className="login__entrada"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••••••"
              required
              value={clave}
              onChange={(evento) => establecerClave(evento.target.value)}
            />
          </div>
          <button type="submit" className="login__boton" disabled={enviando}>
            {enviando ? 'Entrando…' : 'Entrar'}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        </form>
      </main>

      <footer className="login__pie">
        <span className="login__leyenda">
          <span className="punto punto--agua" />
          AGUA · m³
        </span>
        <span className="login__leyenda">
          <span className="punto punto--luz" />
          LUZ · kWh
        </span>
      </footer>
    </div>
  )
}
