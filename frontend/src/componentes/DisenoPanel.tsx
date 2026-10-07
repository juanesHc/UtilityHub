import { useEffect } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'
import { sesionVigente } from '../sesion/almacenSesion'
import { useSesion, type EstadoNavegacionLogin } from '../sesion/contextoSesion'
import { EncabezadoPanel } from './EncabezadoPanel'

export function DisenoPanel() {
  const { sesion } = useSesion()
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  if (!sesionVigente(sesion)) {
    const estado: EstadoNavegacionLogin = sesion === null ? {} : { aviso: 'vencida' }
    return <Navigate to="/login" replace state={estado} />
  }

  return (
    <div className="panel">
      <EncabezadoPanel />
      <Outlet />
    </div>
  )
}
