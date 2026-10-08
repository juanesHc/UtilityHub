from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.almacen_local import TAMANO_MAXIMO_OBJETO_BYTES, AlmacenLocal
from api.configuracion import VARIABLE_CARPETA_ALMACEN_LOCAL
from api.esquemas import (
    AdministradorRespuesta,
    ArchivoDeCargaRespuesta,
    CargaRespuesta,
    DetalleLecturaRespuesta,
    PATRON_TEXTO_SIN_CARACTER_NUL,
    ErrorRespuesta,
    PaginaHistoricoRespuesta,
    RechazoRespuesta,
    ServicioRespuesta,
    SolicitudInicioSesion,
    SolicitudRegistroUsuario,
    SolicitudSubidaArchivo,
    SubidaAutorizadaRespuesta,
    SubidaRespuesta,
    TokenAccesoRespuesta,
    TorreRespuesta,
    UsuarioRegistradoRespuesta,
)
from api.servicio_autenticacion import ServicioAutenticacion, UsuarioAutenticado
from api.servicio_consulta import ServicioConsulta
from api.servicio_subidas import ServicioSubidas
from api.servicio_usuarios import ServicioUsuarios
from api.traduccion import (
    convertir_administrador_en_respuesta,
    CODIGO_HTTP_ENTIDAD_NO_PROCESABLE,
    convertir_carga_en_respuesta,
    convertir_detalle_en_respuesta,
    convertir_pagina_en_respuesta,
    convertir_rechazo_en_respuesta,
    convertir_servicio_en_respuesta,
    convertir_subida_en_respuesta,
    convertir_token_en_respuesta,
    convertir_torre_en_respuesta,
    convertir_usuario_registrado_en_respuesta,
)
from comun.excepciones import AlmacenNoConfigurado, ArchivoDemasiadoGrande, TokenInvalido
from comun.modelos import FiltrosHistoricoLecturas, Periodo, SolicitudPagina
from comun.reloj import obtener_fecha_hora_actual_utc
from procesamiento.receptor_archivos import ReceptorArchivosRecibidos


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


def obtener_servicio_subidas(peticion: Request) -> ServicioSubidas:
    return peticion.app.state.servicio_subidas


def obtener_receptor_archivos(peticion: Request) -> ReceptorArchivosRecibidos:
    return peticion.app.state.receptor_archivos


def obtener_almacen_local(peticion: Request) -> AlmacenLocal:
    almacen_local: AlmacenLocal | None = peticion.app.state.almacen_local
    if almacen_local is None:
        raise AlmacenNoConfigurado(VARIABLE_CARPETA_ALMACEN_LOCAL)
    return almacen_local


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
router_subidas = APIRouter(
    prefix="/api/subidas",
    tags=["Subidas"],
    dependencies=[Depends(exigir_usuario_autenticado)],
    responses=RESPUESTA_NO_AUTENTICADO,
)
router_almacen_local = APIRouter(prefix="/almacen-local", tags=["Almacén local (simula S3)"])


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
    "/cargas/{id_carga}/archivo",
    tags=["Cargas"],
    summary="URL de descarga del archivo original",
    description=(
        "Devuelve una URL firmada, válida por 5 minutos, para leer el CSV original tal como se subió. Es el mismo "
        "contrato que una URL prefirmada de lectura de S3. Solo existe para las cargas que llegaron por subida; "
        "las procesadas desde la línea de comandos responden 404."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorRespuesta, "description": "La carga no existe o no tiene archivo guardado"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorRespuesta, "description": "El almacén de archivos no está configurado"},
    },
)
def obtener_archivo_de_carga(
    id_carga: Annotated[int, Path(ge=1)],
    peticion: Request,
    servicio_subidas: Annotated[ServicioSubidas, Depends(obtener_servicio_subidas)],
    almacen_local: Annotated[AlmacenLocal, Depends(obtener_almacen_local)],
) -> ArchivoDeCargaRespuesta:
    descarga_autorizada = servicio_subidas.autorizar_descarga_de_carga(id_carga)
    firma_de_descarga = almacen_local.firmar("GET", descarga_autorizada.clave_objeto, descarga_autorizada.fecha_expiracion)
    url_objeto = str(peticion.url_for("entregar_objeto_local", clave_objeto=descarga_autorizada.clave_objeto))
    return ArchivoDeCargaRespuesta(
        nombre_archivo=descarga_autorizada.nombre_archivo,
        url_descarga=url_objeto + "?" + urlencode({"expira": firma_de_descarga.expira, "firma": firma_de_descarga.firma}),
        expira_en=descarga_autorizada.fecha_expiracion,
    )


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


@router_subidas.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Solicitar una URL de subida",
    description=(
        "Registra la intención de subir un CSV y devuelve una URL firmada, válida por 5 minutos, a la que el "
        "navegador envía el archivo con PUT. Es el mismo contrato que una URL prefirmada de S3. Antes de firmar "
        "comprueba el nombre del archivo, que la torre exista y que el periodo sea admisible."
    ),
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorRespuesta, "description": "El periodo es anterior al más reciente de la torre"},
        CODIGO_HTTP_ENTIDAD_NO_PROCESABLE: {"model": ErrorRespuesta, "description": "Nombre de archivo o torre no válidos"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorRespuesta, "description": "El almacén de archivos no está configurado"},
    },
)
def solicitar_subida(
    solicitud: SolicitudSubidaArchivo,
    peticion: Request,
    usuario_autenticado: Annotated[UsuarioAutenticado, Depends(exigir_usuario_autenticado)],
    servicio_subidas: Annotated[ServicioSubidas, Depends(obtener_servicio_subidas)],
    almacen_local: Annotated[AlmacenLocal, Depends(obtener_almacen_local)],
) -> SubidaAutorizadaRespuesta:
    subida_autorizada = servicio_subidas.solicitar_subida(solicitud.nombre_archivo, usuario_autenticado)
    firma_de_subida = almacen_local.firmar("PUT", subida_autorizada.clave_objeto, subida_autorizada.fecha_expiracion)
    url_objeto = str(peticion.url_for("recibir_objeto_local", clave_objeto=subida_autorizada.clave_objeto))
    return SubidaAutorizadaRespuesta(
        id_subida=subida_autorizada.id_subida,
        clave_objeto=subida_autorizada.clave_objeto,
        url_subida=url_objeto + "?" + urlencode({"expira": firma_de_subida.expira, "firma": firma_de_subida.firma}),
        metodo="PUT",
        encabezados={"Content-Type": "text/csv"},
        expira_en=subida_autorizada.fecha_expiracion,
    )


@router_subidas.get(
    "/{id_subida}",
    summary="Estado de una subida",
    description=(
        "pendiente mientras el archivo no se ha procesado; procesada con el id_carga resultante; fallida con "
        "detalle_error cuando el archivo no se pudo procesar."
    ),
    responses=RESPUESTA_NO_ENCONTRADO,
)
def consultar_subida(
    id_subida: Annotated[int, Path(ge=1)],
    servicio_subidas: Annotated[ServicioSubidas, Depends(obtener_servicio_subidas)],
) -> SubidaRespuesta:
    return convertir_subida_en_respuesta(servicio_subidas.consultar_subida(id_subida))


@router_almacen_local.put(
    "/{clave_objeto:path}",
    name="recibir_objeto_local",
    summary="Recibir un archivo con URL firmada",
    description=(
        "Sustituto local de S3 para desarrollo. No usa el token JWT: la autorización es la firma de la URL. "
        "Guarda el archivo en la carpeta del almacén y, como lo haría la notificación de S3 a la Lambda, "
        "lo procesa en segundo plano."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"model": ErrorRespuesta, "description": "Firma inválida o vencida"},
        status.HTTP_413_CONTENT_TOO_LARGE: {"model": ErrorRespuesta, "description": "Archivo demasiado grande"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorRespuesta, "description": "El almacén de archivos no está configurado"},
    },
)
async def recibir_objeto_local(
    clave_objeto: str,
    peticion: Request,
    tareas_en_segundo_plano: BackgroundTasks,
    expira: Annotated[int, Query()],
    firma: Annotated[str, Query(pattern=r"^[0-9a-f]{64}$")],
    almacen_local: Annotated[AlmacenLocal, Depends(obtener_almacen_local)],
    receptor_archivos: Annotated[ReceptorArchivosRecibidos, Depends(obtener_receptor_archivos)],
) -> Response:
    almacen_local.verificar_firma("PUT", clave_objeto, expira, firma, obtener_fecha_hora_actual_utc())
    longitud_declarada = peticion.headers.get("content-length", "")
    if longitud_declarada.isdigit() and int(longitud_declarada) > TAMANO_MAXIMO_OBJETO_BYTES:
        raise ArchivoDemasiadoGrande(TAMANO_MAXIMO_OBJETO_BYTES)
    contenido_objeto = await peticion.body()
    if len(contenido_objeto) > TAMANO_MAXIMO_OBJETO_BYTES:
        raise ArchivoDemasiadoGrande(TAMANO_MAXIMO_OBJETO_BYTES)
    almacen_local.guardar_objeto(clave_objeto, contenido_objeto)
    tareas_en_segundo_plano.add_task(receptor_archivos.recibir_objeto, clave_objeto, contenido_objeto)
    return Response(status_code=status.HTTP_200_OK)


@router_almacen_local.get(
    "/{clave_objeto:path}",
    name="entregar_objeto_local",
    summary="Entregar un archivo con URL firmada",
    description="Sustituto local de una URL prefirmada de lectura de S3. La autorización es la firma de la URL.",
    response_class=Response,
    responses={
        status.HTTP_200_OK: {"content": {"text/csv": {}}, "description": "Contenido del archivo tal como se subió"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorRespuesta, "description": "Firma inválida o vencida"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorRespuesta, "description": "El objeto no existe"},
    },
)
def entregar_objeto_local(
    clave_objeto: str,
    expira: Annotated[int, Query()],
    firma: Annotated[str, Query(pattern=r"^[0-9a-f]{64}$")],
    almacen_local: Annotated[AlmacenLocal, Depends(obtener_almacen_local)],
) -> Response:
    almacen_local.verificar_firma("GET", clave_objeto, expira, firma, obtener_fecha_hora_actual_utc())
    return Response(content=almacen_local.leer_objeto(clave_objeto), media_type="text/csv")
