export class ErrorApi extends Error {
  readonly codigoHttp: number | null

  constructor(mensaje: string, codigoHttp: number | null) {
    super(mensaje)
    this.name = new.target.name
    this.codigoHttp = codigoHttp
  }
}

export class ErrorCredencialesInvalidas extends ErrorApi {
  constructor() {
    super('Usuario o clave incorrectos.', 401)
  }
}

export class ErrorCuentaBloqueada extends ErrorApi {
  readonly segundosRestantes: number

  constructor(segundosRestantes: number) {
    super('Cuenta bloqueada por intentos fallidos.', 429)
    this.segundosRestantes = segundosRestantes
  }

  get minutosRestantes(): number {
    return Math.max(1, Math.ceil(this.segundosRestantes / 60))
  }
}

export class ErrorSesionVencida extends ErrorApi {
  constructor() {
    super('La sesión venció o dejó de ser válida.', 401)
  }
}

export class ErrorRecursoInexistente extends ErrorApi {
  constructor(detalle: string) {
    super(detalle, 404)
  }
}

export class ErrorConflicto extends ErrorApi {
  constructor(detalle: string) {
    super(detalle, 409)
  }
}

export class ErrorSolicitudInvalida extends ErrorApi {
  constructor(detalle: string) {
    super(detalle, 422)
  }
}

export class ErrorConexion extends ErrorApi {
  constructor() {
    super('No fue posible conectarse con el servidor.', null)
  }
}

export class ErrorEnvioArchivo extends ErrorApi {
  constructor(codigoHttp: number | null) {
    super(mensajeDeEnvioFallido(codigoHttp), codigoHttp)
  }
}

function mensajeDeEnvioFallido(codigoHttp: number | null): string {
  if (codigoHttp === null) {
    return 'No fue posible enviar el archivo al almacenamiento.'
  }
  if (codigoHttp === 403) {
    return 'El permiso de subida venció o no es válido. Vuelve a intentarlo.'
  }
  if (codigoHttp === 413) {
    return 'El archivo supera el tamaño máximo permitido.'
  }
  return 'El almacenamiento rechazó el archivo.'
}

export class ErrorServidor extends ErrorApi {
  constructor(codigoHttp: number) {
    super('El servidor respondió con un error inesperado.', codigoHttp)
  }
}
