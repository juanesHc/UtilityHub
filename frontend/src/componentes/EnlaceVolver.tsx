import type { MouseEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'

interface PropiedadesEnlaceVolver {
  destinoPorDefecto: string
  texto: string
  className?: string
}

export function EnlaceVolver({ destinoPorDefecto, texto, className }: PropiedadesEnlaceVolver) {
  const navegar = useNavigate()
  const ubicacion = useLocation()

  function volver(evento: MouseEvent<HTMLAnchorElement>) {
    if (ubicacion.key !== 'default') {
      evento.preventDefault()
      navegar(-1)
    }
  }

  return (
    <Link to={destinoPorDefecto} className={className} onClick={volver}>
      ← {texto}
    </Link>
  )
}
