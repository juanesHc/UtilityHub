import type { EstadoCarga } from '../api/tipos'
import { presentarEstadoCarga } from '../dominio/formato'
import './pastillaEstadoCarga.css'

interface PropiedadesPastillaEstadoCarga {
  estado: EstadoCarga
  conPunto?: boolean
}

export function PastillaEstadoCarga({ estado, conPunto = true }: PropiedadesPastillaEstadoCarga) {
  const presentacion = presentarEstadoCarga(estado)
  return (
    <span className={`pastilla-estado-carga pastilla-estado-carga--${estado}`} style={{ color: presentacion.colorTinta }}>
      {conPunto && <span className="pastilla-estado-carga__punto" style={{ background: presentacion.colorPunto }} aria-hidden="true" />}
      {presentacion.nombreVisible}
    </span>
  )
}
