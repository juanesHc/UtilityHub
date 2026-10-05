from fastapi import Request, status
from fastapi.responses import JSONResponse

from api.esquemas import (
    CargaRespuesta,
    DetalleLecturaRespuesta,
    LecturaHistoricoRespuesta,
    PaginaHistoricoRespuesta,
    RechazoRespuesta,
    ServicioRespuesta,
    TokenAccesoRespuesta,
    TorreRespuesta,
)
from api.servicio_autenticacion import TokenEmitido
from comun.excepciones import (
    CargaInexistente,
    CredencialesInvalidas,
    ErrorConexionBaseDatos,
    ErrorUtilityHub,
    LecturaInexistente,
    PeriodoInvalido,
    RangoDePeriodosInvalido,
    TokenInvalido,
)
from comun.modelos import (
    DetalleLecturaExplicada,
    LecturaConsultada,
    PaginaLecturas,
    RechazoRegistrado,
    ResumenCarga,
    Servicio,
    Torre,
)


CODIGO_HTTP_ENTIDAD_NO_PROCESABLE: int = 422
CODIGO_HTTP_POR_EXCEPCION: dict[type[ErrorUtilityHub], int] = {
    CredencialesInvalidas: status.HTTP_401_UNAUTHORIZED,
    TokenInvalido: status.HTTP_401_UNAUTHORIZED,
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
    encabezados = {"WWW-Authenticate": "Bearer"} if codigo_http == status.HTTP_401_UNAUTHORIZED else None
    return JSONResponse(status_code=codigo_http, content={"detail": mensaje}, headers=encabezados)


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
