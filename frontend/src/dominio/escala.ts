const PASOS_REDONDOS: readonly number[] = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]
const MARGEN_SUPERIOR = 1.05

export function calcularMaximoDeEscala(valores: number[]): number {
  const mayor = Math.max(0, ...valores) * MARGEN_SUPERIOR
  if (mayor <= 0) {
    return 1
  }
  const magnitud = 10 ** Math.floor(Math.log10(mayor))
  const paso = PASOS_REDONDOS.find((candidato) => candidato * magnitud >= mayor) ?? 10
  return paso * magnitud
}

export function porcentajeEnEscala(valor: number, maximo: number): number {
  return Math.min(100, Math.max(0, (valor / maximo) * 100))
}
