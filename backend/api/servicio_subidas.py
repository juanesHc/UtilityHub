import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial

from api.servicio_autenticacion import UsuarioAutenticado
from comun import repositorio
from comun.conexion import Conexion as Connection, Cursor
from comun.excepciones import (
    ArchivoDeCargaNoDisponible,
    CargaInexistente,
    NombreArchivoInvalido,
    PeriodoAnteriorAlMasReciente,
    SubidaInexistente,
    TorreInexistente,
)
from comun.modelos import IdentificacionArchivo, SubidaRegistrada
from comun.reloj import obtener_fecha_hora_actual_utc
from comun.transacciones import ejecutar_en_transaccion
from procesamiento.normalizacion import PATRON_SEPARADOR_DE_RUTA, interpretar_nombre_archivo


DURACION_URL_SUBIDA: timedelta = timedelta(minutes=5)
DURACION_URL_DESCARGA: timedelta = timedelta(minutes=5)
PREFIJO_CLAVE_OBJETO: str = "entrada"


@dataclass(frozen=True)
class SubidaAutorizada:
    id_subida: int
    clave_objeto: str
    fecha_expiracion: datetime


@dataclass(frozen=True)
class DescargaAutorizada:
    nombre_archivo: str
    clave_objeto: str
    fecha_expiracion: datetime


def generar_identificador_aleatorio() -> str:
    return uuid.uuid4().hex


class ServicioSubidas:
    def __init__(
        self,
        abrir_conexion: Callable[[], Connection],
        obtener_fecha_hora_actual: Callable[[], datetime] = obtener_fecha_hora_actual_utc,
        generar_identificador: Callable[[], str] = generar_identificador_aleatorio,
    ) -> None:
        self.abrir_conexion: Callable[[], Connection] = abrir_conexion
        self.obtener_fecha_hora_actual: Callable[[], datetime] = obtener_fecha_hora_actual
        self.generar_identificador: Callable[[], str] = generar_identificador

    def solicitar_subida(self, nombre_archivo: str, usuario: UsuarioAutenticado) -> SubidaAutorizada:
        if PATRON_SEPARADOR_DE_RUTA.search(nombre_archivo) or nombre_archivo != nombre_archivo.strip():
            raise NombreArchivoInvalido(nombre_archivo)
        identificacion_archivo = interpretar_nombre_archivo(nombre_archivo)
        fecha_solicitud = self.obtener_fecha_hora_actual()
        clave_objeto = f"{PREFIJO_CLAVE_OBJETO}/{self.generar_identificador()}/{nombre_archivo}"
        id_subida = ejecutar_en_transaccion(
            self.abrir_conexion,
            partial(
                registrar_subida_si_el_periodo_es_admisible,
                identificacion_archivo=identificacion_archivo,
                clave_objeto=clave_objeto,
                nombre_archivo=nombre_archivo,
                id_usuario=usuario.id_usuario,
                fecha_solicitud=fecha_solicitud,
            ),
        )
        return SubidaAutorizada(
            id_subida=id_subida,
            clave_objeto=clave_objeto,
            fecha_expiracion=fecha_solicitud + DURACION_URL_SUBIDA,
        )

    def consultar_subida(self, id_subida: int) -> SubidaRegistrada:
        subida = ejecutar_en_transaccion(self.abrir_conexion, partial(repositorio.buscar_subida_por_id, id_subida=id_subida))
        if subida is None:
            raise SubidaInexistente(id_subida)
        return subida

    def autorizar_descarga_de_carga(self, id_carga: int) -> DescargaAutorizada:
        subida = ejecutar_en_transaccion(self.abrir_conexion, partial(buscar_subida_de_carga_existente, id_carga=id_carga))
        return DescargaAutorizada(
            nombre_archivo=subida.nombre_archivo,
            clave_objeto=subida.clave_objeto,
            fecha_expiracion=self.obtener_fecha_hora_actual() + DURACION_URL_DESCARGA,
        )


def buscar_subida_de_carga_existente(cursor: Cursor, id_carga: int) -> SubidaRegistrada:
    if not repositorio.existe_carga(cursor, id_carga):
        raise CargaInexistente(id_carga)
    subida = repositorio.buscar_subida_por_id_carga(cursor, id_carga)
    if subida is None:
        raise ArchivoDeCargaNoDisponible(id_carga)
    return subida


def registrar_subida_si_el_periodo_es_admisible(
    cursor: Cursor,
    identificacion_archivo: IdentificacionArchivo,
    clave_objeto: str,
    nombre_archivo: str,
    id_usuario: int,
    fecha_solicitud: datetime,
) -> int:
    torre = repositorio.buscar_torre_por_codigo(cursor, identificacion_archivo.codigo_torre)
    if torre is None:
        raise TorreInexistente(identificacion_archivo.codigo_torre)
    periodo_mas_reciente = repositorio.buscar_periodo_mas_reciente_con_lecturas(cursor, torre.id_torre)
    if periodo_mas_reciente is not None and identificacion_archivo.periodo < periodo_mas_reciente:
        raise PeriodoAnteriorAlMasReciente(
            torre.codigo,
            identificacion_archivo.periodo.como_texto(),
            periodo_mas_reciente.como_texto(),
        )
    return repositorio.insertar_subida(cursor, clave_objeto, nombre_archivo, id_usuario, fecha_solicitud)
