from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.esquemas import (
    CargaRespuesta,
    DetalleLecturaRespuesta,
    ErrorRespuesta,
    PaginaHistoricoRespuesta,
    RechazoRespuesta,
    ServicioRespuesta,
    SolicitudInicioSesion,
    TokenAccesoRespuesta,
    TorreRespuesta,
)
from api.servicio_autenticacion import ServicioAutenticacion, UsuarioAutenticado
from api.servicio_consulta import ServicioConsulta
from api.traduccion import (
    CODIGO_HTTP_ENTIDAD_NO_PROCESABLE,
    convertir_carga_en_respuesta,
    convertir_detalle_en_respuesta,
    convertir_pagina_en_respuesta,
    convertir_rechazo_en_respuesta,
    convertir_servicio_en_respuesta,
    convertir_token_en_respuesta,
    convertir_torre_en_respuesta,
)
from comun.excepciones import TokenInvalido
from comun.modelos import FiltrosHistoricoLecturas, Periodo, SolicitudPagina


PATRON_PERIODO_API: str = r"^[0-9]{4}-(0[1-9]|1[0-2])$"
TAMANO_PAGINA_POR_DEFECTO: int = 50
TAMANO_PAGINA_MAXIMO: int = 200

RESPUESTA_NO_AUTENTICADO: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorRespuesta, "description": "Token ausente, invalido o vencido"},
}
RESPUESTA_NO_ENCONTRADO: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"model": ErrorRespuesta, "description": "El recurso no existe"},
}

esquema_token_portador = HTTPBearer(
    auto_error=False,
    description="Token JWT obtenido en POST /api/auth/login",
)


def obtener_servicio_consulta(peticion: Request) -> ServicioConsulta:
    return peticion.app.state.servicio_consulta


def obtener_servicio_autenticacion(peticion: Request) -> ServicioAutenticacion:
    return peticion.app.state.servicio_autenticacion


def exigir_usuario_autenticado(
    servicio_autenticacion: Annotated[ServicioAutenticacion, Depends(obtener_servicio_autenticacion)],
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_token_portador)],
) -> UsuarioAutenticado:
    if credenciales is None:
        raise TokenInvalido()
    return servicio_autenticacion.verificar_token(credenciales.credentials)


router_autenticacion = APIRouter(prefix="/api/auth", tags=["Autenticacion"])
router_consulta = APIRouter(
    prefix="/api",
    dependencies=[Depends(exigir_usuario_autenticado)],
    responses=RESPUESTA_NO_AUTENTICADO,
)


@router_autenticacion.post(
    "/login",
    summary="Iniciar sesion",
    description=(
        "Verifica usuario y clave contra la tabla USUARIO, registra el ultimo acceso y devuelve "
        "un token JWT valido por 8 horas. Envie el token en el encabezado Authorization: Bearer <token>."
    ),
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorRespuesta, "description": "Credenciales incorrectas"}},
)
def iniciar_sesion(
    solicitud: SolicitudInicioSesion,
    servicio_autenticacion: Annotated[ServicioAutenticacion, Depends(obtener_servicio_autenticacion)],
) -> TokenAccesoRespuesta:
    token_emitido = servicio_autenticacion.iniciar_sesion(solicitud.usuario, solicitud.clave)
    return convertir_token_en_respuesta(token_emitido)


@router_consulta.get(
    "/lecturas",
    tags=["Consulta"],
    summary="Historico de lecturas",
    description=(
        "Lecturas consolidadas, ordenadas por periodo descendente. Todos los filtros son opcionales y se "
        "combinan entre si. La respuesta incluye la pagina solicitada y el total de resultados del filtro."
    ),
    responses={CODIGO_HTTP_ENTIDAD_NO_PROCESABLE: {"model": ErrorRespuesta, "description": "Filtros invalidos"}},
)
def consultar_historico_lecturas(
    servicio_consulta: Annotated[ServicioConsulta, Depends(obtener_servicio_consulta)],
    torre: Annotated[str | None, Query(max_length=10, description="Codigo de torre, por ejemplo T01")] = None,
    apartamento: Annotated[str | None, Query(max_length=10, description="Numero de apartamento, por ejemplo 101")] = None,
    servicio: Annotated[str | None, Query(max_length=20, description="Codigo de servicio, por ejemplo AGUA")] = None,
    periodo_desde: Annotated[str | None, Query(pattern=PATRON_PERIODO_API, description="AAAA-MM inclusive")] = None,
    periodo_hasta: Annotated[str | None, Query(pattern=PATRON_PERIODO_API, description="AAAA-MM inclusive")] = None,
    solo_anomalos: Annotated[bool, Query(description="Si es verdadero, devuelve solo consumos anomalos")] = False,
    pagina: Annotated[int, Query(ge=1, description="Numero de pagina, desde 1")] = 1,
    tamano_pagina: Annotated[int, Query(ge=1, le=TAMANO_PAGINA_MAXIMO)] = TAMANO_PAGINA_POR_DEFECTO,
) -> PaginaHistoricoRespuesta:
    filtros = FiltrosHistoricoLecturas(
        codigo_torre=torre,
        numero_apartamento=apartamento,
        codigo_servicio=servicio,
        periodo_desde=None if periodo_desde is None else Periodo.desde_texto(periodo_desde),
        periodo_hasta=None if periodo_hasta is None else Periodo.desde_texto(periodo_hasta),
        solo_anomalos=solo_anomalos,
    )
    solicitud_pagina = SolicitudPagina(numero_pagina=pagina, tamano_pagina=tamano_pagina)
    pagina_lecturas = servicio_consulta.consultar_historico_lecturas(filtros, solicitud_pagina)
    return convertir_pagina_en_respuesta(pagina_lecturas)


@router_consulta.get(
    "/lecturas/{id_lectura}",
    tags=["Consulta"],
    summary="Detalle de una lectura",
    description=(
        "Devuelve la lectura con todo lo necesario para explicar la evaluacion: consumo del periodo, "
        "promedio de referencia, umbral del servicio, rango de consumo normal y desviacion relativa. "
        "fue_evaluada es falso en la linea base o cuando no hay historial para comparar. El umbral es el "
        "vigente hoy en SERVICIO."
    ),
    responses=RESPUESTA_NO_ENCONTRADO,
)
def obtener_detalle_lectura(
    id_lectura: Annotated[int, Path(ge=1)],
    servicio_consulta: Annotated[ServicioConsulta, Depends(obtener_servicio_consulta)],
) -> DetalleLecturaRespuesta:
    return convertir_detalle_en_respuesta(servicio_consulta.obtener_detalle_lectura(id_lectura))


@router_consulta.get(
    "/cargas",
    tags=["Cargas"],
    summary="Listado de cargas",
    description=(
        "Todas las cargas, de la mas reciente a la mas antigua, con el conteo de filas aceptadas y "
        "rechazadas. Una carga reemplazada muestra 0 aceptadas porque sus lecturas se borraron al reprocesar."
    ),
)
def listar_cargas(
    servicio_consulta: Annotated[ServicioConsulta, Depends(obtener_servicio_consulta)],
) -> list[CargaRespuesta]:
    return [convertir_carga_en_respuesta(resumen_carga) for resumen_carga in servicio_consulta.listar_cargas()]


@router_consulta.get(
    "/cargas/{id_carga}/rechazos",
    tags=["Cargas"],
    summary="Filas rechazadas de una carga",
    description="Filas descartadas durante el procesamiento de la carga, con su numero de fila y su motivo.",
    responses=RESPUESTA_NO_ENCONTRADO,
)
def listar_rechazos_de_carga(
    id_carga: Annotated[int, Path(ge=1)],
    servicio_consulta: Annotated[ServicioConsulta, Depends(obtener_servicio_consulta)],
) -> list[RechazoRespuesta]:
    return [convertir_rechazo_en_respuesta(rechazo) for rechazo in servicio_consulta.listar_rechazos_de_carga(id_carga)]


@router_consulta.get(
    "/torres",
    tags=["Catalogos"],
    summary="Catalogo de torres",
    description="Torres registradas, para poblar los filtros del frontend.",
)
def listar_torres(
    servicio_consulta: Annotated[ServicioConsulta, Depends(obtener_servicio_consulta)],
) -> list[TorreRespuesta]:
    return [convertir_torre_en_respuesta(torre) for torre in servicio_consulta.listar_torres()]


@router_consulta.get(
    "/servicios",
    tags=["Catalogos"],
    summary="Catalogo de servicios",
    description="Servicios registrados con su unidad de medida y umbral de desviacion.",
)
def listar_servicios(
    servicio_consulta: Annotated[ServicioConsulta, Depends(obtener_servicio_consulta)],
) -> list[ServicioRespuesta]:
    return [convertir_servicio_en_respuesta(servicio) for servicio in servicio_consulta.listar_servicios()]
