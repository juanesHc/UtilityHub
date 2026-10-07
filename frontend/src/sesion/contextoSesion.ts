import { createContext, useContext } from 'react'
import type { ClienteApi } from '../api/tipos'
import type { SesionGuardada } from './almacenSesion'

export type AvisoDeLogin = 'vencida'

export interface EstadoNavegacionLogin {
  aviso?: AvisoDeLogin
}

export interface ValorContextoSesion {
  sesion: SesionGuardada | null
  cliente: ClienteApi
  abrirSesion: (token: string) => SesionGuardada | null
  cerrarSesion: () => void
}

export const ContextoSesion = createContext<ValorContextoSesion | null>(null)

export function useSesion(): ValorContextoSesion {
  const valor = useContext(ContextoSesion)
  if (valor === null) {
    throw new Error('useSesion debe usarse dentro de ProveedorSesion')
  }
  return valor
}
