import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import cache, partial

import jwt

from comun import repositorio
from comun.conexion import Conexion as Connection, Cursor
from comun.contrasenas import generar_hash_contrasena, verificar_contrasena
from comun.excepciones import CredencialesInvalidas, CuentaBloqueada, TokenInvalido
from comun.modelos import Usuario
from comun.reloj import obtener_fecha_hora_actual_utc
from comun.transacciones import ejecutar_en_transaccion


ALGORITMO_FIRMA_TOKEN: str = "HS256"
DURACION_TOKEN: timedelta = timedelta(hours=8)
RECLAMOS_OBLIGATORIOS_TOKEN: list[str] = ["sub", "iat", "exp", "ver"]
MAXIMO_INTENTOS_FALLIDOS: int = 5
DURACION_BLOQUEO: timedelta = timedelta(minutes=15)


@dataclass(frozen=True)
class TokenEmitido:
    token_acceso: str
    fecha_expiracion: datetime
    duracion_segundos: int


@dataclass(frozen=True)
class ReclamosToken:
    nombre_usuario: str
    version_credenciales: int


@dataclass(frozen=True)
class UsuarioAutenticado:
    id_usuario: int
    nombre_usuario: str


@dataclass(frozen=True)
class EstadoBloqueo:
    intentos_fallidos: int
    bloqueado_hasta: datetime | None


class ResultadoIntentoInicioSesion(Enum):
    ACEPTADO = "aceptado"
    CREDENCIALES_INVALIDAS = "credenciales_invalidas"
    CUENTA_BLOQUEADA = "cuenta_bloqueada"


@dataclass(frozen=True)
class DesenlaceInicioSesion:
    resultado: ResultadoIntentoInicioSesion
    usuario: Usuario | None = None
    bloqueado_hasta: datetime | None = None


@cache
def obtener_hash_para_usuario_inexistente() -> str:
    return generar_hash_contrasena("usuario-inexistente")


def esta_bloqueado(usuario: Usuario, fecha_actual: datetime) -> bool:
    return usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta > fecha_actual


def calcular_estado_tras_intento_fallido(usuario: Usuario, fecha_actual: datetime) -> EstadoBloqueo:
    intentos_previos = 0 if usuario.bloqueado_hasta is not None else usuario.intentos_fallidos
    intentos_fallidos = intentos_previos + 1
    if intentos_fallidos >= MAXIMO_INTENTOS_FALLIDOS:
        return EstadoBloqueo(intentos_fallidos=intentos_fallidos, bloqueado_hasta=fecha_actual + DURACION_BLOQUEO)
    return EstadoBloqueo(intentos_fallidos=intentos_fallidos, bloqueado_hasta=None)


def calcular_segundos_restantes(bloqueado_hasta: datetime, fecha_actual: datetime) -> int:
    return max(1, math.ceil((bloqueado_hasta - fecha_actual).total_seconds()))


class ServicioAutenticacion:
    def __init__(
        self,
        abrir_conexion: Callable[[], Connection],
        clave_firma_token: str,
        obtener_fecha_hora_actual: Callable[[], datetime] = obtener_fecha_hora_actual_utc,
    ) -> None:
        self.abrir_conexion: Callable[[], Connection] = abrir_conexion
        self.clave_firma_token: str = clave_firma_token
        self.obtener_fecha_hora_actual: Callable[[], datetime] = obtener_fecha_hora_actual

    def iniciar_sesion(self, nombre_usuario: str, clave_en_claro: str) -> TokenEmitido:
        fecha_inicio_sesion = self.obtener_fecha_hora_actual()
        desenlace = ejecutar_en_transaccion(
            self.abrir_conexion,
            partial(
                self.registrar_intento_de_inicio_sesion,
                nombre_usuario=nombre_usuario,
                clave_en_claro=clave_en_claro,
                fecha_inicio_sesion=fecha_inicio_sesion,
            ),
        )
        if desenlace.resultado is ResultadoIntentoInicioSesion.CUENTA_BLOQUEADA and desenlace.bloqueado_hasta is not None:
            raise CuentaBloqueada(calcular_segundos_restantes(desenlace.bloqueado_hasta, fecha_inicio_sesion))
        if desenlace.resultado is not ResultadoIntentoInicioSesion.ACEPTADO or desenlace.usuario is None:
            raise CredencialesInvalidas()
        return self.emitir_token(
            desenlace.usuario.nombre_usuario,
            desenlace.usuario.version_credenciales,
            fecha_inicio_sesion,
        )

    def registrar_intento_de_inicio_sesion(
        self,
        cursor: Cursor,
        nombre_usuario: str,
        clave_en_claro: str,
        fecha_inicio_sesion: datetime,
    ) -> DesenlaceInicioSesion:
        usuario = repositorio.bloquear_usuario_por_nombre(cursor, nombre_usuario)
        if usuario is None:
            verificar_contrasena(clave_en_claro, obtener_hash_para_usuario_inexistente())
            return DesenlaceInicioSesion(ResultadoIntentoInicioSesion.CREDENCIALES_INVALIDAS)
        if esta_bloqueado(usuario, fecha_inicio_sesion):
            return DesenlaceInicioSesion(ResultadoIntentoInicioSesion.CUENTA_BLOQUEADA, bloqueado_hasta=usuario.bloqueado_hasta)
        if not verificar_contrasena(clave_en_claro, usuario.hash_contrasena):
            estado_bloqueo = calcular_estado_tras_intento_fallido(usuario, fecha_inicio_sesion)
            repositorio.registrar_intento_fallido(
                cursor,
                usuario.id_usuario,
                estado_bloqueo.intentos_fallidos,
                estado_bloqueo.bloqueado_hasta,
            )
            if estado_bloqueo.bloqueado_hasta is not None:
                return DesenlaceInicioSesion(
                    ResultadoIntentoInicioSesion.CUENTA_BLOQUEADA,
                    bloqueado_hasta=estado_bloqueo.bloqueado_hasta,
                )
            return DesenlaceInicioSesion(ResultadoIntentoInicioSesion.CREDENCIALES_INVALIDAS)
        repositorio.registrar_inicio_sesion_exitoso(cursor, usuario.id_usuario, fecha_inicio_sesion)
        return DesenlaceInicioSesion(ResultadoIntentoInicioSesion.ACEPTADO, usuario=usuario)

    def emitir_token(self, nombre_usuario: str, version_credenciales: int, fecha_inicio_sesion: datetime) -> TokenEmitido:
        fecha_emision = fecha_inicio_sesion.replace(tzinfo=UTC)
        fecha_expiracion = fecha_emision + DURACION_TOKEN
        token_acceso = jwt.encode(
            {"sub": nombre_usuario, "ver": version_credenciales, "iat": fecha_emision, "exp": fecha_expiracion},
            self.clave_firma_token,
            algorithm=ALGORITMO_FIRMA_TOKEN,
        )
        return TokenEmitido(
            token_acceso=token_acceso,
            fecha_expiracion=fecha_expiracion,
            duracion_segundos=int(DURACION_TOKEN.total_seconds()),
        )

    def decodificar_token(self, token_acceso: str) -> ReclamosToken:
        try:
            reclamos = jwt.decode(
                token_acceso,
                self.clave_firma_token,
                algorithms=[ALGORITMO_FIRMA_TOKEN],
                options={"require": RECLAMOS_OBLIGATORIOS_TOKEN},
            )
        except jwt.PyJWTError as error:
            raise TokenInvalido() from error
        version_credenciales = reclamos["ver"]
        if not isinstance(version_credenciales, int) or isinstance(version_credenciales, bool):
            raise TokenInvalido()
        return ReclamosToken(nombre_usuario=reclamos["sub"], version_credenciales=version_credenciales)

    def verificar_token(self, token_acceso: str) -> UsuarioAutenticado:
        reclamos = self.decodificar_token(token_acceso)
        usuario = ejecutar_en_transaccion(
            self.abrir_conexion,
            partial(repositorio.buscar_usuario_por_nombre, nombre_usuario=reclamos.nombre_usuario),
        )
        if usuario is None or usuario.version_credenciales != reclamos.version_credenciales:
            raise TokenInvalido()
        return UsuarioAutenticado(id_usuario=usuario.id_usuario, nombre_usuario=usuario.nombre_usuario)
