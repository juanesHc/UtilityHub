import { Link, NavLink } from 'react-router'
import { iniciales } from '../dominio/formato'
import { useSesion } from '../sesion/contextoSesion'
import './encabezadoPanel.css'

const ENLACES_DE_NAVEGACION = [
  { destino: '/inicio', texto: 'Inicio' },
  { destino: '/historico', texto: 'Histórico' },
  { destino: '/cargas', texto: 'Cargas' },
  { destino: '/administradores', texto: 'Administradores' },
] as const

export function EncabezadoPanel() {
  const { sesion, cerrarSesion } = useSesion()
  const nombreUsuario = sesion?.nombreUsuario ?? ''

  return (
    <header className="encabezado-panel">
      <Link to="/inicio" className="logo">
        Utility<span className="logo__ligero">Hub</span>
      </Link>
      <nav className="encabezado-panel__navegacion" aria-label="Principal">
        {ENLACES_DE_NAVEGACION.map((enlace) => (
          <NavLink key={enlace.destino} to={enlace.destino} className="encabezado-panel__enlace">
            {enlace.texto}
          </NavLink>
        ))}
      </nav>
      <div className="encabezado-panel__usuario">
        <span className="encabezado-panel__identidad">
          <span className="encabezado-panel__avatar" aria-hidden="true">
            {iniciales(nombreUsuario)}
          </span>
          <span>
            <span className="visualmente-oculto">Sesión iniciada como </span>
            {nombreUsuario}
          </span>
        </span>
        <button type="button" className="encabezado-panel__salir" onClick={cerrarSesion}>
          Salir
        </button>
      </div>
    </header>
  )
}
