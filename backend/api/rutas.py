from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.esquemas import (
    AdministradorRespuesta,
    CargaRespuesta,
    DetalleLecturaRespuesta,
    PATRON_TEXTO_SIN_CARACTER_NUL,
    ErrorRespuesta,
    PaginaHistoricoRespuesta,
    RechazoRespuesta,
    ServicioRespuesta,
    SolicitudInicioSesion,
    SolicitudRegistroUsuario,
    TokenAccesoRespuesta,
    TorreRespuesta,
    UsuarioRegistradoRespuesta,
)
from api.servicio_autenticacion import ServicioAutenticacion, UsuarioAutenticado
from api.servicio_consulta import ServicioConsulta
from api.servicio_usuarios import ServicioUsuarios
from api.traduccion import (
    convertir_administrador_en_respuesta,
    CODIGO_HTTP_ENTIDAD_NO_PROCESABLE,
    convertir_carga_en_respuesta,
    convertir_detalle_en_respuesta,
    convertir_pagina_en_respuesta,
    convertir_rechazo_en_respuesta,
    convertir_servicio_en_respuesta,
    convertir_token_en_respuesta,
    convertir_torre_en_respuesta,
    convertir_usuario_registrado_en_respuesta,
)
from comun.excepciones import TokenInvalido
from comun.modelos import FiltrosHistoricoLecturas, Periodo, SolicitudPagina


PATRON_PERIODO_API: str = r"^[0-9]{4}-(0[1-9]|1[0-2])$"
TAMANO_PAGINA_POR_DEFECTO: int = 50
TAMANO_PAGINA_MAXIMO: int = 200

RESPUESTA_NO_AUTENTICADO: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorRespuesta, "description": "Token ausente, inválido o vencido"},
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


def obtener_servicio_usuarios(peticion: Request) -> ServicioUsuarios:
    return peticion.app.state.servicio_usuarios


def exigir_usuario_autenticado(
    servicio_autenticacion: Annotated[ServicioAutenticacion, Depends(obtener_servicio_autenticacion)],
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_token_portador)],
) -> UsuarioAutenticado:
    if credenciales is None:
        raise TokenInvalido()
    return servicio_autenticacion.verificar_token(credenciales.credentials)


router_autenticacion = APIRouter(prefix="/api/auth", tags=["Autenticación"])
router_consulta = APIRouter(
    prefix="/api",
    dependencies=[Depends(exigir_usuario_autenticado)],
    responses=RESPUESTA_NO_AUTENTICADO,
)
router_usuarios = APIRouter(prefix="/api/usuarios", tags=["Usuarios"], responses=RESPUESTA_NO_AUTENTICADO)


@router_autenticacion.post(
    "/login",
    summary="Iniciar sesión",
    description=(
        "Verifica usuario y clave contra la tabla USUARIO, registra el último acceso y devuelve "
        "un token JWT válido por 8 horas. Envíe el token en el encabezado Authorization: Bearer <token>. "
        "Tras 5 intentos fallidos seguidos la cuenta queda bloqueada 15 minutos, incluso para la clave correcta."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorRespuesta, "description": "Credenciales incorrectas"},
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErrorRespuesta,
            "description": "Cuenta bloqueada temporalmente; el encabezado Retry-After indica los segundos restantes",
        },
    },
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
    summary="Histórico de lecturas",
    description=(
        "Lecturas consolidadas, ordenadas por periodo descendente. Todos los filtros son opcionales y se "
        "combinan entre sí. La respuesta incluye la página solicitada y el total de resultados del filtro."
    ),
    responses={CODIGO_HTTP_ENTIDAD_NO_PROCESABLE: {"model": ErrorRespuesta, "description": "Filtros invalidos"}},
)
def consultar_historico_lecturas(
    servicio_consulta: Annotated[ServicioConsulta, Depends(obtener_servicio_consulta)],
    torre: Annotated[str | None, Query(max_length=10, pattern=PATRON_TEXTO_SIN_CARACTER_NUL, description="Código de torre, por ejemplo T01")] = None,
    apartamento: Annotated[str | None, Query(max_length=10, pattern=PATRON_TEXTO_SIN_CARACTER_NUL, description="Número de apartamento, por ejemplo 101")] = None,
    servicio: Annotated[str | None, Query(max_length=20, pattern=PATRON_TEXTO_SIN_CARACTER_NUL, description="Código de servicio, por ejemplo AGUA")] = None,
    periodo_desde: Annotated[str | None, Query(pattern=PATRON_PERIODO_API, description="AAAA-MM inclusive")] = None,
    periodo_hasta: Annotated[str | None, Query(pattern=PATRON_PERIODO_API, description="AAAA-MM inclusive")] = None,
    solo_anomalos: Annotated[bool, Query(description="Si es verdadero, devuelve solo consumos anómalos")] = False,
    pagina: Annotated[int, Query(ge=1, description="Número de página, desde 1")] = 1,
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
        "Devuelve la lectura con todo lo necesario para explicar la evaluación: consumo del periodo, "
        "promedio de referencia, umbral del servicio, rango de consumo normal y desviación relativa. "
        "fue_evaluada es falso en la línea base o cuando no hay historial para comparar. El umbral es el "
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
        "Todas las cargas, de la más reciente a la más antigua, con el conteo de filas aceptadas y "
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
    description="Filas descartadas durante el procesamiento de la carga, con su número de fila y su motivo.",
    responses=RESPUESTA_NO_ENCONTRADO,
)
def listar_rechazos_de_carga(
    id_carga: Annotated[int, Path(ge=1)],
    servicio_consulta: Annotated[ServicioConsulta, Depends(obtener_servicio_consulta)],
) -> list[RechazoRespuesta]:
    return [convertir_rechazo_en_respuesta(rechazo) for rechazo in servicio_consulta.listar_rechazos_de_carga(id_carga)]


@router_consulta.get(
    "/torres",
    tags=["Catálogos"],
    summary="Catálogo de torres",
    description="Torres registradas, para poblar los filtros del frontend.",
)
def listar_torres(
    servicio_consulta: Annotated[ServicioConsulta, Depends(obtener_servicio_consulta)],
) -> list[TorreRespuesta]:
    return [convertir_torre_en_respuesta(torre) for torre in servicio_consulta.listar_torres()]


@router_consulta.get(
    "/servicios",
    tags=["Catálogos"],
    summary="Catálogo de servicios",
    description="Servicios registrados con su unidad de medida y umbral de desviación.",
)
def listar_servicios(
    servicio_consulta: Annotated[ServicioConsulta, Depends(obtener_servicio_consulta)],
) -> list[ServicioRespuesta]:
    return [convertir_servicio_en_respuesta(servicio) for servicio in servicio_consulta.listar_servicios()]


@router_usuarios.get(
    "",
    summary="Listar administradores",
    description=(
        "Todos los administradores, ordenados por nombre, con quién los creó, cuándo y su último acceso. "
        "esta_bloqueado indica si la cuenta está bloqueada ahora por intentos fallidos. Nunca incluye la clave."
    ),
    dependencies=[Depends(exigir_usuario_autenticado)],
)
def listar_administradores(
    servicio_usuarios: Annotated[ServicioUsuarios, Depends(obtener_servicio_usuarios)],
) -> list[AdministradorRespuesta]:
    return [convertir_administrador_en_respuesta(administrador) for administrador in servicio_usuarios.listar_administradores()]


@router_usuarios.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un administrador",
    description=(
        "Crea un usuario nuevo con acceso completo a la API. Solo puede hacerlo un usuario autenticado, "
        "y queda registrado quién lo creó. El nombre no distingue mayúsculas y no puede repetirse; "
        "la clave debe tener entre 12 y 128 caracteres."
    ),
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorRespuesta, "description": "Ya existe un usuario con ese nombre"},
        CODIGO_HTTP_ENTIDAD_NO_PROCESABLE: {"model": ErrorRespuesta, "description": "Nombre o clave no aceptables"},
    },
)
def registrar_usuario(
    solicitud: SolicitudRegistroUsuario,
    usuario_autenticado: Annotated[UsuarioAutenticado, Depends(exigir_usuario_autenticado)],
    servicio_usuarios: Annotated[ServicioUsuarios, Depends(obtener_servicio_usuarios)],
) -> UsuarioRegistradoRespuesta:
    usuario_registrado = servicio_usuarios.registrar_usuario(solicitud.usuario, solicitud.clave, usuario_autenticado)
    return convertir_usuario_registrado_en_respuesta(usuario_registrado)
