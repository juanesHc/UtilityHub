import { useEffect, useState } from 'react'
import { ErrorSesionVencida } from '../../api/errores'
import type { AdministradorListado, ClienteApi } from '../../api/tipos'
import { formatearFechaHora, pluralizar } from '../../dominio/formato'

interface PropiedadesListaAdministradores {
  cliente: ClienteApi
  versionDeLista: number
  nombreUsuarioActual: string | null
}

interface RespuestaLista {
  estado: 'lista' | 'error'
  administradores: AdministradorListado[]
}

function Administrador({ administrador, esActual }: { administrador: AdministradorListado; esActual: boolean }) {
  const origen =
    administrador.creado_por === null
      ? 'Creado en la instalación'
      : `Creado por ${administrador.creado_por}${administrador.fecha_creacion === null ? '' : ` · ${formatearFechaHora(administrador.fecha_creacion)}`}`
  return (
    <li className="administradores-lista__fila">
      <div className="administradores-lista__datos">
        <div className="administradores-lista__nombre">
          {administrador.nombre_usuario}
          {esActual && <span className="administradores-lista__actual"> (tú)</span>}
        </div>
        <div className="administradores-lista__detalle">{origen}</div>
        <div className="administradores-lista__detalle">
          {administrador.ultimo_acceso === null
            ? 'Todavía no ha iniciado sesión'
            : `Último acceso · ${formatearFechaHora(administrador.ultimo_acceso)}`}
        </div>
      </div>
      {administrador.esta_bloqueado ? (
        <span className="administradores-lista__estado-cuenta administradores-lista__estado-cuenta--bloqueada">Bloqueada</span>
      ) : (
        <span className="administradores-lista__estado-cuenta">Activa</span>
      )}
    </li>
  )
}

export function ListaAdministradores({ cliente, versionDeLista, nombreUsuarioActual }: PropiedadesListaAdministradores) {
  const [respuesta, establecerRespuesta] = useState<RespuestaLista | null>(null)
  const [intento, establecerIntento] = useState(0)

  useEffect(() => {
    let vigente = true
    cliente
      .listarAdministradores()
      .then((administradores) => {
        if (vigente) {
          establecerRespuesta({ estado: 'lista', administradores })
        }
      })
      .catch((error: unknown) => {
        if (vigente && !(error instanceof ErrorSesionVencida)) {
          establecerRespuesta({ estado: 'error', administradores: [] })
        }
      })
    return () => {
      vigente = false
    }
  }, [cliente, versionDeLista, intento])

  const administradores = respuesta?.administradores ?? []
  const actual = nombreUsuarioActual?.toLowerCase() ?? null

  return (
    <aside className="administradores-lista" aria-labelledby="titulo-lista-administradores" aria-busy={respuesta === null}>
      <div className="administradores-lista__cabecera">
        <h2 id="titulo-lista-administradores" className="administradores-lista__titulo">
          Administradores
        </h2>
        {respuesta?.estado === 'lista' && (
          <span className="administradores-lista__conteo">
            {administradores.length} {pluralizar(administradores.length, 'cuenta', 'cuentas')}
          </span>
        )}
      </div>

      {respuesta === null && <p className="administradores-lista__cargando">Cargando administradores…</p>}

      {respuesta?.estado === 'error' && (
        <div className="administradores-aviso administradores-lista__error" role="alert">
          <span>No pudimos cargar la lista de administradores.</span>
          <button
            type="button"
            className="administradores-boton-enlace"
            onClick={() => {
              establecerRespuesta(null)
              establecerIntento((anterior) => anterior + 1)
            }}
          >
            Reintentar
          </button>
        </div>
      )}

      {respuesta?.estado === 'lista' && (
        <ul className="administradores-lista__filas">
          {administradores.map((administrador) => (
            <Administrador
              key={administrador.id_usuario}
              administrador={administrador}
              esActual={administrador.nombre_usuario.toLowerCase() === actual}
            />
          ))}
        </ul>
      )}
    </aside>
  )
}
