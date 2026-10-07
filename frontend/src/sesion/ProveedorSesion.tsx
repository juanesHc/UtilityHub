import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { crearClienteApi } from '../api/cliente'
import { ErrorSesionVencida } from '../api/errores'
import type { ClienteApi } from '../api/tipos'
import { borrarToken, guardarToken, leerSesionGuardada, leerTokenActual, sesionVigente, type SesionGuardada } from './almacenSesion'
import { ContextoSesion, type EstadoNavegacionLogin } from './contextoSesion'

const RETRASO_MAXIMO_DE_TEMPORIZADOR = 2_147_483_647

function vigilarVencimiento(cliente: ClienteApi, alVencer: () => void): ClienteApi {
  return new Proxy(cliente, {
    get(objetivo, propiedad, receptor) {
      const valor: unknown = Reflect.get(objetivo, propiedad, receptor)
      if (typeof valor !== 'function') {
        return valor
      }
      return async (...argumentos: unknown[]) => {
        try {
          return await (valor as (...parametros: unknown[]) => Promise<unknown>).apply(objetivo, argumentos)
        } catch (error) {
          if (error instanceof ErrorSesionVencida) {
            alVencer()
          }
          throw error
        }
      }
    },
  })
}

function leerSesionVigente(): SesionGuardada | null {
  const guardada = leerSesionGuardada()
  return sesionVigente(guardada) ? guardada : null
}

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const navegar = useNavigate()
  const [sesion, establecerSesion] = useState<SesionGuardada | null>(leerSesionVigente)

  const expirarSesion = useCallback(() => {
    borrarToken()
    establecerSesion(null)
    const estado: EstadoNavegacionLogin = { aviso: 'vencida' }
    navegar('/login', { replace: true, state: estado })
  }, [navegar])

  const cliente = useMemo(() => vigilarVencimiento(crearClienteApi(leerTokenActual), expirarSesion), [expirarSesion])

  const abrirSesion = useCallback((token: string) => {
    guardarToken(token)
    const guardada = leerSesionGuardada()
    establecerSesion(guardada)
    return guardada
  }, [])

  const cerrarSesion = useCallback(() => {
    borrarToken()
    establecerSesion(null)
    navegar('/login', { replace: true })
  }, [navegar])

  useEffect(() => {
    if (sesion === null) {
      return undefined
    }
    const restante = Math.min(sesion.expiraEnMilisegundos - Date.now(), RETRASO_MAXIMO_DE_TEMPORIZADOR)
    const temporizador = window.setTimeout(expirarSesion, Math.max(0, restante))
    return () => window.clearTimeout(temporizador)
  }, [sesion, expirarSesion])

  const valor = useMemo(() => ({ sesion, cliente, abrirSesion, cerrarSesion }), [sesion, cliente, abrirSesion, cerrarSesion])
  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>
}
