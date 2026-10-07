import { leerReclamosDelToken } from './token'

const CLAVE_TOKEN = 'utilityhub.token'

let tokenEnMemoria: string | null = null

export interface SesionGuardada {
  token: string
  nombreUsuario: string
  expiraEnMilisegundos: number
}

export function leerTokenActual(): string | null {
  if (tokenEnMemoria !== null) {
    return tokenEnMemoria
  }
  try {
    return window.localStorage.getItem(CLAVE_TOKEN)
  } catch {
    return null
  }
}

export function leerSesionGuardada(): SesionGuardada | null {
  const token = leerTokenActual()
  if (token === null) {
    return null
  }
  const reclamos = leerReclamosDelToken(token)
  return reclamos === null ? null : { token, ...reclamos }
}

export function guardarToken(token: string): void {
  tokenEnMemoria = token
  try {
    window.localStorage.setItem(CLAVE_TOKEN, token)
  } catch {
    return
  }
}

export function borrarToken(): void {
  tokenEnMemoria = null
  try {
    window.localStorage.removeItem(CLAVE_TOKEN)
  } catch {
    return
  }
}

export function sesionVigente(sesion: SesionGuardada | null): sesion is SesionGuardada {
  return sesion !== null && sesion.expiraEnMilisegundos > Date.now()
}
