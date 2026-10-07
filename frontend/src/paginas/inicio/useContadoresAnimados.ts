import { useEffect, useState } from 'react'
import { prefiereMovimientoReducido } from '../../dominio/medios'

const INTERVALO_MILISEGUNDOS = 120
const PASOS_MINIMOS = 7
const PASOS_MAXIMOS = 12

export interface ValoresContadores {
  anomalias: number
  problemas: number
}

interface EstadoContadores {
  objetivo: ValoresContadores | null
  paso: number
}

const CONTADORES_EN_CERO: ValoresContadores = { anomalias: 0, problemas: 0 }

function calcularPasos(objetivo: ValoresContadores): number {
  return Math.min(PASOS_MAXIMOS, Math.max(PASOS_MINIMOS, objetivo.anomalias))
}

function valoresEnPaso(objetivo: ValoresContadores, paso: number): ValoresContadores {
  const pasos = calcularPasos(objetivo)
  return {
    anomalias: Math.round((objetivo.anomalias * paso) / pasos),
    problemas: Math.min(objetivo.problemas, Math.floor((objetivo.problemas * paso) / (pasos - 1))),
  }
}

export function useContadoresAnimados(objetivo: ValoresContadores | null): ValoresContadores {
  const [movimientoReducido] = useState(prefiereMovimientoReducido)
  const [estado, establecerEstado] = useState<EstadoContadores>({ objetivo, paso: 0 })

  if (estado.objetivo !== objetivo) {
    establecerEstado({ objetivo, paso: 0 })
  }

  useEffect(() => {
    if (objetivo === null || movimientoReducido) {
      return undefined
    }
    const pasos = calcularPasos(objetivo)
    const temporizador = window.setInterval(() => {
      establecerEstado((actual) => {
        if (actual.objetivo !== objetivo || actual.paso >= pasos) {
          window.clearInterval(temporizador)
          return actual
        }
        return { objetivo, paso: actual.paso + 1 }
      })
    }, INTERVALO_MILISEGUNDOS)
    return () => window.clearInterval(temporizador)
  }, [objetivo, movimientoReducido])

  if (objetivo === null) {
    return CONTADORES_EN_CERO
  }
  return movimientoReducido ? objetivo : valoresEnPaso(objetivo, estado.objetivo === objetivo ? estado.paso : 0)
}
