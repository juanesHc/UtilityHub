export interface ReclamosDelToken {
  nombreUsuario: string
  expiraEnMilisegundos: number
}

function decodificarBase64Url(texto: string): string {
  const base64 = texto.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(texto.length / 4) * 4, '=')
  const binario = atob(base64)
  const bytes = Uint8Array.from(binario, (caracter) => caracter.charCodeAt(0))
  return new TextDecoder().decode(bytes)
}

export function leerReclamosDelToken(token: string): ReclamosDelToken | null {
  const contenido = token.split('.')[1]
  if (contenido === undefined) {
    return null
  }
  try {
    const reclamos: unknown = JSON.parse(decodificarBase64Url(contenido))
    if (typeof reclamos !== 'object' || reclamos === null) {
      return null
    }
    const { sub, exp } = reclamos as { sub?: unknown; exp?: unknown }
    if (typeof sub !== 'string' || typeof exp !== 'number') {
      return null
    }
    return { nombreUsuario: sub, expiraEnMilisegundos: exp * 1000 }
  } catch {
    return null
  }
}
