import { useId, useRef, useState, type FormEvent } from 'react'
import { ErrorConexion, ErrorConflicto, ErrorSesionVencida, ErrorSolicitudInvalida } from '../../api/errores'
import type { UsuarioRegistrado } from '../../api/tipos'
import { formatearFechaHora } from '../../dominio/formato'
import { rutaMedio } from '../../dominio/medios'
import {
  generarClaveSegura,
  reglasDeClave,
  reglasDeNombre,
  todasCumplidas,
  type ReglaCumplida,
} from '../../dominio/reglasUsuario'
import { useSesion } from '../../sesion/contextoSesion'
import { ListaAdministradores } from './ListaAdministradores'
import './administradores.css'

type EstadoCopia = 'sin-copiar' | 'copiada' | 'fallo'

function ListaDeReglas({ identificador, reglas, mostrarIncumplidas }: { identificador: string; reglas: ReglaCumplida[]; mostrarIncumplidas: boolean }) {
  return (
    <ul id={identificador} className="administradores-reglas">
      {reglas.map((regla) => (
        <li
          key={regla.identificador}
          className={
            regla.cumplida
              ? 'administradores-regla administradores-regla--cumplida'
              : mostrarIncumplidas
                ? 'administradores-regla administradores-regla--incumplida'
                : 'administradores-regla'
          }
        >
          <span className="administradores-regla__marca" aria-hidden="true">
            {regla.cumplida ? '✓' : mostrarIncumplidas ? '!' : '·'}
          </span>
          {regla.descripcion}
          <span className="visualmente-oculto">{regla.cumplida ? ' (cumplida)' : ' (pendiente)'}</span>
        </li>
      ))}
    </ul>
  )
}

function traducirError(error: unknown): string {
  if (error instanceof ErrorConflicto) {
    return 'Ya existe un administrador con ese nombre (sin distinguir mayúsculas). Elige otro.'
  }
  if (error instanceof ErrorSolicitudInvalida) {
    return `El servidor no aceptó los datos: ${error.message}`
  }
  if (error instanceof ErrorConexion) {
    return 'No pudimos conectarnos con el servidor. Revisa tu conexión e inténtalo de nuevo.'
  }
  return 'Ocurrió un error inesperado al registrar el administrador.'
}

export function PaginaAdministradores() {
  const { cliente, sesion } = useSesion()
  const identificadorBase = useId()
  const [nombreUsuario, establecerNombreUsuario] = useState('')
  const [clave, establecerClave] = useState('')
  const [confirmacion, establecerConfirmacion] = useState('')
  const [claveVisible, establecerClaveVisible] = useState(false)
  const [intentoEnviar, establecerIntentoEnviar] = useState(false)
  const [enviando, establecerEnviando] = useState(false)
  const [errorServidor, establecerErrorServidor] = useState<string | null>(null)
  const [registrado, establecerRegistrado] = useState<UsuarioRegistrado | null>(null)
  const [estadoCopia, establecerEstadoCopia] = useState<EstadoCopia>('sin-copiar')
  const [versionDeLista, establecerVersionDeLista] = useState(0)
  const campoNombre = useRef<HTMLInputElement>(null)
  const campoClave = useRef<HTMLInputElement>(null)
  const campoConfirmacion = useRef<HTMLInputElement>(null)

  const reglasNombre = reglasDeNombre(nombreUsuario)
  const reglasClave = reglasDeClave(clave, confirmacion)
  const nombreValido = todasCumplidas(reglasNombre)
  const claveValida = todasCumplidas(reglasClave.filter((regla) => regla.identificador !== 'clave-coincide'))
  const confirmacionValida = reglasClave.find((regla) => regla.identificador === 'clave-coincide')?.cumplida ?? false
  const idReglasNombre = `${identificadorBase}-reglas-nombre`
  const idReglasClave = `${identificadorBase}-reglas-clave`

  function generarClave() {
    const generada = generarClaveSegura()
    establecerClave(generada)
    establecerConfirmacion(generada)
    establecerClaveVisible(true)
    establecerEstadoCopia('sin-copiar')
  }

  async function copiarClave() {
    try {
      await navigator.clipboard.writeText(clave)
      establecerEstadoCopia('copiada')
    } catch {
      establecerEstadoCopia('fallo')
    }
  }

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (enviando) {
      return
    }
    establecerIntentoEnviar(true)
    establecerErrorServidor(null)
    if (!nombreValido) {
      campoNombre.current?.focus()
      return
    }
    if (!claveValida) {
      campoClave.current?.focus()
      return
    }
    if (!confirmacionValida) {
      campoConfirmacion.current?.focus()
      return
    }
    establecerEnviando(true)
    try {
      const usuarioRegistrado = await cliente.registrarUsuario(nombreUsuario, clave)
      establecerRegistrado(usuarioRegistrado)
      establecerVersionDeLista((anterior) => anterior + 1)
      establecerNombreUsuario('')
      establecerClave('')
      establecerConfirmacion('')
      establecerClaveVisible(false)
      establecerIntentoEnviar(false)
      establecerEstadoCopia('sin-copiar')
    } catch (error) {
      if (!(error instanceof ErrorSesionVencida)) {
        establecerErrorServidor(traducirError(error))
      }
    } finally {
      establecerEnviando(false)
    }
  }

  function registrarOtro() {
    establecerRegistrado(null)
    window.setTimeout(() => campoNombre.current?.focus(), 0)
  }

  return (
    <div className="administradores">
      <section className="administradores-heroe">
        <div className="administradores-heroe__fondo anim-acercamiento">
          <img src={rutaMedio('residential-towers-sunset.jpg')} alt="" className="administradores-heroe__foto" />
        </div>
        <div className="administradores-heroe__degradado" />
        <div className="administradores-heroe__contenido">
          <p className="etiqueta-mono administradores-heroe__etiqueta administradores-ascenso-1">Accesos</p>
          <h1 className="administradores-heroe__titular administradores-ascenso-2">Administradores</h1>
          <p className="administradores-heroe__descripcion administradores-ascenso-2">
            Registra a otra persona para que consulte lecturas, cargas y anomalías del conjunto.
          </p>
        </div>
      </section>

      <section className="administradores-cuerpo">
        <div className="administradores-columna-formulario">
          {registrado !== null ? (
            <div className="administradores-exito" role="status">
              <p className="etiqueta-mono administradores-exito__etiqueta">Administrador registrado</p>
              <h2 className="administradores-exito__nombre">{registrado.nombre_usuario}</h2>
              <p className="administradores-exito__detalle">
                Creado por <strong>{registrado.creado_por ?? sesion?.nombreUsuario ?? 'ti'}</strong> el{' '}
                {formatearFechaHora(registrado.fecha_creacion)}.
              </p>
              <p className="administradores-exito__detalle">
                Entrégale la clave por un canal seguro, fuera de esta aplicación. No se volverá a mostrar.
              </p>
              <button type="button" className="administradores-boton-principal" onClick={registrarOtro}>
                Registrar otro administrador
              </button>
            </div>
          ) : (
            <form className="administradores-formulario" onSubmit={enviar} noValidate aria-busy={enviando}>
              <h2 className="administradores-formulario__titulo">Registrar un administrador</h2>

              {errorServidor !== null && (
                <p role="alert" className="administradores-aviso">
                  {errorServidor}
                </p>
              )}

              <div className="administradores-campo">
                <label htmlFor={`${identificadorBase}-nombre`}>Usuario</label>
                <input
                  ref={campoNombre}
                  id={`${identificadorBase}-nombre`}
                  className="administradores-entrada"
                  type="text"
                  autoComplete="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  maxLength={60}
                  placeholder="admin.porteria"
                  aria-describedby={idReglasNombre}
                  aria-invalid={intentoEnviar && !nombreValido}
                  value={nombreUsuario}
                  onChange={(evento) => {
                    establecerNombreUsuario(evento.target.value)
                    establecerErrorServidor(null)
                  }}
                />
                <ListaDeReglas identificador={idReglasNombre} reglas={reglasNombre} mostrarIncumplidas={intentoEnviar} />
              </div>

              <div className="administradores-campo">
                <div className="administradores-campo__cabecera">
                  <label htmlFor={`${identificadorBase}-clave`}>Clave</label>
                  <button type="button" className="administradores-boton-enlace" onClick={generarClave}>
                    Generar clave segura
                  </button>
                </div>
                <div className="administradores-entrada-con-accion">
                  <input
                    ref={campoClave}
                    id={`${identificadorBase}-clave`}
                    className="administradores-entrada"
                    type={claveVisible ? 'text' : 'password'}
                    autoComplete="new-password"
                    spellCheck={false}
                    maxLength={140}
                    aria-describedby={idReglasClave}
                    aria-invalid={intentoEnviar && !claveValida}
                    value={clave}
                    onChange={(evento) => {
                      establecerClave(evento.target.value)
                      establecerEstadoCopia('sin-copiar')
                    }}
                  />
                  <button
                    type="button"
                    className="administradores-boton-icono"
                    aria-label={claveVisible ? 'Ocultar clave' : 'Mostrar clave'}
                    aria-pressed={claveVisible}
                    onClick={() => establecerClaveVisible((actual) => !actual)}
                  >
                    {claveVisible ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M3 3l18 18M10.6 10.6a2 2 0 002.8 2.8M9.9 5.1A9.8 9.8 0 0112 5c5 0 9 4.5 10 7-.4 1-1.3 2.4-2.6 3.7M6.1 6.1C4.1 7.5 2.6 9.5 2 12c1 2.5 5 7 10 7 1.6 0 3.1-.4 4.4-1.1" />
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M2 12c1-2.5 5-7 10-7s9 4.5 10 7c-1 2.5-5 7-10 7S3 14.5 2 12z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                  {claveVisible && clave !== '' && (
                    <button type="button" className="administradores-boton-copiar" onClick={copiarClave}>
                      {estadoCopia === 'copiada' ? 'Copiada' : 'Copiar'}
                    </button>
                  )}
                </div>
                {estadoCopia === 'fallo' && (
                  <p className="administradores-ayuda" role="status">
                    El navegador no permitió copiar. Selecciona la clave y cópiala a mano.
                  </p>
                )}
              </div>

              <div className="administradores-campo">
                <label htmlFor={`${identificadorBase}-confirmacion`}>Confirmar clave</label>
                <input
                  ref={campoConfirmacion}
                  id={`${identificadorBase}-confirmacion`}
                  className="administradores-entrada"
                  type={claveVisible ? 'text' : 'password'}
                  autoComplete="new-password"
                  spellCheck={false}
                  maxLength={140}
                  aria-describedby={idReglasClave}
                  aria-invalid={intentoEnviar && !confirmacionValida}
                  value={confirmacion}
                  onChange={(evento) => establecerConfirmacion(evento.target.value)}
                />
                <ListaDeReglas identificador={idReglasClave} reglas={reglasClave} mostrarIncumplidas={intentoEnviar} />
              </div>

              <button type="submit" className="administradores-boton-principal" disabled={enviando}>
                {enviando ? 'Registrando…' : 'Registrar administrador'}
              </button>
            </form>
          )}
        </div>

        <ListaAdministradores cliente={cliente} versionDeLista={versionDeLista} nombreUsuarioActual={sesion?.nombreUsuario ?? null} />
      </section>
    </div>
  )
}
