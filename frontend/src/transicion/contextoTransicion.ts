import { createContext, useContext } from 'react'

export type EtapaTransicion = 'inactiva' | 'preparada' | 'cubriendo' | 'revelando'

export interface ValorTransicion {
  etapa: EtapaTransicion
  prepararTransicion: () => () => void
  iniciarTransicion: (destino: string) => void
}

export const ContextoTransicion = createContext<ValorTransicion | null>(null)

export function useTransicionDeNube(): ValorTransicion {
  const valor = useContext(ContextoTransicion)
  if (valor === null) {
    throw new Error('useTransicionDeNube debe usarse dentro de ProveedorTransicionDeNube')
  }
  return valor
}
