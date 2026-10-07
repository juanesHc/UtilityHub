from fastapi import Request, status
from fastapi.responses import JSONResponse

from api.esquemas import (
    AdministradorRespuesta,
    CargaRespuesta,
    DetalleLecturaRespuesta,
    LecturaHistoricoRespuesta,
    PaginaHistoricoRespuesta,
    RechazoRespuesta,
    ServicioRespuesta,
    TokenAccesoRespuesta,
    TorreRespuesta,
    UsuarioRegistradoRespuesta,
)
from api.servicio_autenticacion import TokenEmitido
from api.servicio_usuarios import AdministradorListado
from comun.excepciones import (
    CargaInexistente,
    ClaveInsegura,
    CredencialesInvalidas,
    CuentaBloqueada,
    ErrorConexionBaseDatos,
    ErrorUtilityHub,
    LecturaInexistente,
    NombreUsuarioInvalido,
    PeriodoInvalido,
    RangoDePeriodosInvalido,
    TokenInvalido,
    UsuarioYaExiste,
)
from comun.modelos import (
    DetalleLecturaExplicada,
    LecturaConsultada,
    PaginaLecturas,
    RechazoRegistrado,
    ResumenCarga,
    Servicio,
    Torre,
    UsuarioRegistrado,
)


CODIGO_HTTP_ENTIDAD_NO_PROCESABLE: int = 422
CODIGO_HTTP_POR_EXCEPCION: dict[type[ErrorUtilityHub], int] = {
    CredencialesInvalidas: status.HTTP_401_UNAUTHORIZED,
    TokenInvalido: status.HTTP_401_UNAUTHORIZED,
    CuentaBloqueada: status.HTTP_429_TOO_MANY_REQUESTS,
    UsuarioYaExiste: status.HTTP_409_CONFLICT,
    NombreUsuarioInvalido: CODIGO_HTTP_ENTIDAD_NO_PROCESABLE,
    ClaveInsegura: CODIGO_HTTP_ENTIDAD_NO_PROCESABLE,
    LecturaInexistente: status.HTTP_404_NOT_FOUND,
    CargaInexistente: status.HTTP_404_NOT_FOUND,
    PeriodoInvalido: CODIGO_HTTP_ENTIDAD_NO_PROCESABLE,
    RangoDePeriodosInvalido: CODIGO_HTTP_ENTIDAD_NO_PROCESABLE,
    ErrorConexionBaseDatos: status.HTTP_503_SERVICE_UNAVAILABLE,
}
MENSAJE_ERROR_INTERNO: str = "Error interno del servidor"


def traducir_error_de_dominio(peticion: Request, error: Exception) -> JSONResponse:
    codigo_http = next(
        (
            CODIGO_HTTP_POR_EXCEPCION[tipo_excepcion]
            for tipo_excepcion in type(error).__mro__
            if tipo_excepcion in CODIGO_HTTP_POR_EXCEPCION
        ),
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    mensaje = str(error) if codigo_http != status.HTTP_500_INTERNAL_SERVER_ERROR else MENSAJE_ERROR_INTERNO
    return JSONResponse(status_code=codigo_http, content={"detail": mensaje}, headers=construir_encabezados_de_error(error, codigo_http))


def construir_encabezados_de_error(error: Exception, codigo_http: int) -> dict[str, str] | None:
    if codigo_http == status.HTTP_401_UNAUTHORIZED:
        return {"WWW-Authenticate": "Bearer"}
    if isinstance(error, CuentaBloqueada):
        return {"Retry-After": str(error.segundos_restantes)}
    return None


def convertir_administrador_en_respuesta(administrador: AdministradorListado) -> AdministradorRespuesta:
    return AdministradorRespuesta(
        id_usuario=administrador.id_usuario,
        nombre_usuario=administrador.nombre_usuario,
        fecha_creacion=administrador.fecha_creacion,
        creado_por=administrador.nombre_usuario_creador,
        ultimo_acceso=administrador.ultimo_acceso,
        esta_bloqueado=administrador.esta_bloqueado,
    )


def convertir_usuario_registrado_en_respuesta(usuario_registrado: UsuarioRegistrado) -> UsuarioRegistradoRespuesta:
    return UsuarioRegistradoRespuesta(
        id_usuario=usuario_registrado.id_usuario,
        nombre_usuario=usuario_registrado.nombre_usuario,
        fecha_creacion=usuario_registrado.fecha_creacion,
        creado_por=usuario_registrado.nombre_usuario_creador,
    )


def convertir_token_en_respuesta(token_emitido: TokenEmitido) -> TokenAccesoRespuesta:
    return TokenAccesoRespuesta(
        token_acceso=token_emitido.token_acceso,
        tipo_token="bearer",
        expira_en=token_emitido.fecha_expiracion,
        duracion_segundos=token_emitido.duracion_segundos,
    )


def convertir_lectura_en_respuesta_historico(lectura: LecturaConsultada) -> LecturaHistoricoRespuesta:
    return LecturaHistoricoRespuesta(
        id_lectura=lectura.id_lectura,
        codigo_torre=lectura.codigo_torre,
        nombre_torre=lectura.nombre_torre,
        numero_apartamento=lectura.numero_apartamento,
        codigo_servicio=lectura.codigo_servicio,
        nombre_servicio=lectura.nombre_servicio,
        unidad_medida=lectura.unidad_medida,
        periodo=lectura.periodo.como_texto(),
        lectura_acumulada=lectura.lectura_acumulada,
        consumo_periodo=lectura.consumo_periodo,
        fecha_lectura=lectura.fecha_lectura,
        promedio_referencia=lectura.promedio_referencia,
        es_anomalo=lectura.es_anomalo,
    )


def convertir_pagina_en_respuesta(pagina_lecturas: PaginaLecturas) -> PaginaHistoricoRespuesta:
    return PaginaHistoricoRespuesta(
        lecturas=[convertir_lectura_en_respuesta_historico(lectura) for lectura in pagina_lecturas.lecturas],
        pagina=pagina_lecturas.solicitud_pagina.numero_pagina,
        tamano_pagina=pagina_lecturas.solicitud_pagina.tamano_pagina,
        total_resultados=pagina_lecturas.total_resultados,
        total_paginas=pagina_lecturas.total_paginas,
    )


def convertir_detalle_en_respuesta(detalle_lectura: DetalleLecturaExplicada) -> DetalleLecturaRespuesta:
    lectura = detalle_lectura.lectura
    rango_consumo_normal = detalle_lectura.rango_consumo_normal
    return DetalleLecturaRespuesta(
        id_lectura=lectura.id_lectura,
        id_carga=lectura.id_carga,
        codigo_torre=lectura.codigo_torre,
        nombre_torre=lectura.nombre_torre,
        numero_apartamento=lectura.numero_apartamento,
        codigo_servicio=lectura.codigo_servicio,
        nombre_servicio=lectura.nombre_servicio,
        unidad_medida=lectura.unidad_medida,
        periodo=lectura.periodo.como_texto(),
        fecha_lectura=lectura.fecha_lectura,
        lectura_acumulada=lectura.lectura_acumulada,
        consumo_periodo=lectura.consumo_periodo,
        promedio_referencia=lectura.promedio_referencia,
        umbral_desviacion=lectura.umbral_desviacion,
        limite_inferior_normal=None if rango_consumo_normal is None else rango_consumo_normal.limite_inferior,
        limite_superior_normal=None if rango_consumo_normal is None else rango_consumo_normal.limite_superior,
        desviacion_relativa=detalle_lectura.desviacion_relativa,
        fue_evaluada=rango_consumo_normal is not None,
        es_anomalo=lectura.es_anomalo,
    )


def convertir_carga_en_respuesta(resumen_carga: ResumenCarga) -> CargaRespuesta:
    return CargaRespuesta(
        id_carga=resumen_carga.id_carga,
        codigo_torre=resumen_carga.codigo_torre,
        nombre_torre=resumen_carga.nombre_torre,
        periodo=resumen_carga.periodo.como_texto(),
        nombre_archivo=resumen_carga.nombre_archivo,
        fecha_procesamiento=resumen_carga.fecha_procesamiento,
        estado=resumen_carga.estado.value,
        filas_aceptadas=resumen_carga.cantidad_lecturas_aceptadas,
        filas_rechazadas=resumen_carga.cantidad_filas_rechazadas,
    )


def convertir_rechazo_en_respuesta(rechazo: RechazoRegistrado) -> RechazoRespuesta:
    return RechazoRespuesta(
        id_rechazo=rechazo.id_rechazo,
        numero_fila=rechazo.numero_fila,
        apartamento=rechazo.apartamento,
        servicio=rechazo.servicio,
        periodo=rechazo.periodo,
        motivo=rechazo.motivo_rechazo.value,
        valor_recibido=rechazo.valor_recibido,
    )


def convertir_torre_en_respuesta(torre: Torre) -> TorreRespuesta:
    return TorreRespuesta(id_torre=torre.id_torre, codigo=torre.codigo, nombre=torre.nombre)


def convertir_servicio_en_respuesta(servicio: Servicio) -> ServicioRespuesta:
    return ServicioRespuesta(
        id_servicio=servicio.id_servicio,
        codigo=servicio.codigo,
        nombre=servicio.nombre,
        unidad_medida=servicio.unidad_medida,
        umbral_desviacion=servicio.umbral_desviacion,
    )
