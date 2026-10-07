import { ClienteHttp } from './clienteHttp'
import type { ClienteApi } from './tipos'

export function leerUrlApi(): string | null {
  const urlApi = import.meta.env.VITE_API_URL?.trim() ?? ''
  return urlApi === '' ? null : urlApi
}

export function crearClienteApi(obtenerToken: () => string | null): ClienteApi {
  const urlApi = leerUrlApi()
  if (urlApi === null) {
    throw new Error('Falta VITE_API_URL: define la URL de la API en frontend/.env.development o frontend/.env.production')
  }
  return new ClienteHttp(urlApi, obtenerToken)
}
