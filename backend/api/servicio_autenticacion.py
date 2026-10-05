from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache, partial

import jwt
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from comun import repositorio
from comun.contrasenas import generar_hash_contrasena, verificar_contrasena
from comun.excepciones import CredencialesInvalidas, TokenInvalido
from comun.reloj import obtener_fecha_hora_actual_utc
from comun.transacciones import ejecutar_en_transaccion


ALGORITMO_FIRMA_TOKEN: str = "HS256"
DURACION_TOKEN: timedelta = timedelta(hours=8)
RECLAMOS_OBLIGATORIOS_TOKEN: list[str] = ["sub", "iat", "exp"]


@dataclass(frozen=True)
class TokenEmitido:
    token_acceso: str
    fecha_expiracion: datetime
    duracion_segundos: int


@dataclass(frozen=True)
class UsuarioAutenticado:
    nombre_usuario: str


@cache
def obtener_hash_para_usuario_inexistente() -> str:
    return generar_hash_contrasena("usuario-inexistente")


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
        ejecutar_en_transaccion(
            self.abrir_conexion,
            partial(
                self.verificar_credenciales_y_registrar_acceso,
                nombre_usuario=nombre_usuario,
                clave_en_claro=clave_en_claro,
                fecha_inicio_sesion=fecha_inicio_sesion,
            ),
        )
        return self.emitir_token(nombre_usuario, fecha_inicio_sesion)

    def verificar_credenciales_y_registrar_acceso(
        self,
        cursor: Cursor,
        nombre_usuario: str,
        clave_en_claro: str,
        fecha_inicio_sesion: datetime,
    ) -> None:
        usuario = repositorio.buscar_usuario_por_nombre(cursor, nombre_usuario)
        if usuario is None:
            verificar_contrasena(clave_en_claro, obtener_hash_para_usuario_inexistente())
            raise CredencialesInvalidas()
        if not verificar_contrasena(clave_en_claro, usuario.hash_contrasena):
            raise CredencialesInvalidas()
        repositorio.registrar_ultimo_acceso(cursor, usuario.id_usuario, fecha_inicio_sesion)

    def emitir_token(self, nombre_usuario: str, fecha_inicio_sesion: datetime) -> TokenEmitido:
        fecha_emision = fecha_inicio_sesion.replace(tzinfo=UTC)
        fecha_expiracion = fecha_emision + DURACION_TOKEN
        token_acceso = jwt.encode(
            {"sub": nombre_usuario, "iat": fecha_emision, "exp": fecha_expiracion},
            self.clave_firma_token,
            algorithm=ALGORITMO_FIRMA_TOKEN,
        )
        return TokenEmitido(
            token_acceso=token_acceso,
            fecha_expiracion=fecha_expiracion,
            duracion_segundos=int(DURACION_TOKEN.total_seconds()),
        )

    def verificar_token(self, token_acceso: str) -> UsuarioAutenticado:
        try:
            reclamos = jwt.decode(
                token_acceso,
                self.clave_firma_token,
                algorithms=[ALGORITMO_FIRMA_TOKEN],
                options={"require": RECLAMOS_OBLIGATORIOS_TOKEN},
            )
        except jwt.PyJWTError as error:
            raise TokenInvalido() from error
        return UsuarioAutenticado(nombre_usuario=reclamos["sub"])
