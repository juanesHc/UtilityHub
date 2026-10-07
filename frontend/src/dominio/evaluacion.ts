export interface RangoConsumoNormal {
  limiteInferior: number
  limiteSuperior: number
}

export function calcularRangoConsumoNormal(promedioReferencia: number, umbralDesviacion: number): RangoConsumoNormal {
  const desviacionTolerada = promedioReferencia * umbralDesviacion
  return {
    limiteInferior: Math.max(0, promedioReferencia - desviacionTolerada),
    limiteSuperior: promedioReferencia + desviacionTolerada,
  }
}

export function calcularDesviacionRelativa(consumoPeriodo: number, promedioReferencia: number): number | null {
  if (promedioReferencia === 0) {
    return null
  }
  return (consumoPeriodo - promedioReferencia) / promedioReferencia
}

export function esConsumoAnomalo(consumoPeriodo: number, promedioReferencia: number, umbralDesviacion: number): boolean {
  const rango = calcularRangoConsumoNormal(promedioReferencia, umbralDesviacion)
  return consumoPeriodo < rango.limiteInferior || consumoPeriodo > rango.limiteSuperior
}
