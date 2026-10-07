from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial

from api.servicio_autenticacion import UsuarioAutenticado
from comun import repositorio
from comun.conexion import Conexion as Connection, Cursor
from comun.contrasenas import generar_hash_contrasena
from comun.excepciones import ClaveInsegura, NombreUsuarioInvalido, UsuarioInexistente, UsuarioYaExiste
from comun.modelos import UsuarioRegistrado
from comun.reloj import obtener_fecha_hora_actual_utc
from comun.transacciones import ejecutar_en_transaccion


LONGITUD_MAXIMA_NOMBRE_USUARIO: int = 50
LONGITUD_MINIMA_CLAVE: int = 12
LONGITUD_MAXIMA_CLAVE: int = 128
CARACTER_NUL: str = "\x00"


@dataclass(frozen=True)
class AdministradorListado:
    id_usuario: int
    nombre_usuario: str
    fecha_creacion: datetime | None
    nombre_usuario_creador: str | None
    ultimo_acceso: datetime | None
    esta_bloqueado: bool


class ServicioUsuarios:
    def __init__(
        self,
        abrir_conexion: Callable[[], Connection],
        obtener_fecha_hora_actual: Callable[[], datetime] = obtener_fecha_hora_actual_utc,
    ) -> None:
        self.abrir_conexion: Callable[[], Connection] = abrir_conexion
        self.obtener_fecha_hora_actual: Callable[[], datetime] = obtener_fecha_hora_actual

    def registrar_usuario(
        self,
        nombre_usuario: str,
        clave_en_claro: str,
        creador: UsuarioAutenticado | None = None,
    ) -> UsuarioRegistrado:
        validar_nombre_usuario(nombre_usuario)
        validar_clave(clave_en_claro)
        hash_contrasena = generar_hash_contrasena(clave_en_claro)
        return ejecutar_en_transaccion(
            self.abrir_conexion,
            partial(
                insertar_usuario_si_no_existe,
                nombre_usuario=nombre_usuario,
                hash_contrasena=hash_contrasena,
                fecha_creacion=self.obtener_fecha_hora_actual(),
                creador=creador,
            ),
        )

    def listar_administradores(self) -> tuple[AdministradorListado, ...]:
        fecha_actual = self.obtener_fecha_hora_actual()
        usuarios = ejecutar_en_transaccion(self.abrir_conexion, repositorio.listar_usuarios)
        return tuple(
            AdministradorListado(
                id_usuario=usuario.id_usuario,
                nombre_usuario=usuario.nombre_usuario,
                fecha_creacion=usuario.fecha_creacion,
                nombre_usuario_creador=usuario.nombre_usuario_creador,
                ultimo_acceso=usuario.ultimo_acceso,
                esta_bloqueado=usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta > fecha_actual,
            )
            for usuario in usuarios
        )

    def cambiar_clave(self, nombre_usuario: str, clave_nueva_en_claro: str) -> None:
        validar_clave(clave_nueva_en_claro)
        hash_contrasena = generar_hash_contrasena(clave_nueva_en_claro)
        ejecutar_en_transaccion(
            self.abrir_conexion,
            partial(reemplazar_clave_de_usuario_existente, nombre_usuario=nombre_usuario, hash_contrasena=hash_contrasena),
        )


def insertar_usuario_si_no_existe(
    cursor: Cursor,
    nombre_usuario: str,
    hash_contrasena: str,
    fecha_creacion: datetime,
    creador: UsuarioAutenticado | None,
) -> UsuarioRegistrado:
    if repositorio.buscar_usuario_por_nombre(cursor, nombre_usuario) is not None:
        raise UsuarioYaExiste(nombre_usuario)
    id_usuario = repositorio.insertar_usuario(
        cursor,
        nombre_usuario,
        hash_contrasena,
        fecha_creacion,
        None if creador is None else creador.id_usuario,
    )
    return UsuarioRegistrado(
        id_usuario=id_usuario,
        nombre_usuario=nombre_usuario,
        fecha_creacion=fecha_creacion,
        nombre_usuario_creador=None if creador is None else creador.nombre_usuario,
    )


def reemplazar_clave_de_usuario_existente(cursor: Cursor, nombre_usuario: str, hash_contrasena: str) -> None:
    usuario = repositorio.buscar_usuario_por_nombre(cursor, nombre_usuario)
    if usuario is None:
        raise UsuarioInexistente(nombre_usuario)
    repositorio.actualizar_clave_e_invalidar_sesiones(cursor, usuario.id_usuario, hash_contrasena)


def validar_nombre_usuario(nombre_usuario: str) -> None:
    if nombre_usuario == "" or nombre_usuario != nombre_usuario.strip():
        raise NombreUsuarioInvalido(nombre_usuario, "no puede estar vacío ni empezar o terminar con espacios")
    if len(nombre_usuario) > LONGITUD_MAXIMA_NOMBRE_USUARIO:
        raise NombreUsuarioInvalido(nombre_usuario, f"supera {LONGITUD_MAXIMA_NOMBRE_USUARIO} caracteres")
    if CARACTER_NUL in nombre_usuario or not nombre_usuario.isprintable():
        raise NombreUsuarioInvalido(nombre_usuario, "contiene caracteres de control")


def validar_clave(clave_en_claro: str) -> None:
    if len(clave_en_claro) < LONGITUD_MINIMA_CLAVE:
        raise ClaveInsegura(f"debe tener al menos {LONGITUD_MINIMA_CLAVE} caracteres")
    if len(clave_en_claro) > LONGITUD_MAXIMA_CLAVE:
        raise ClaveInsegura(f"no puede superar {LONGITUD_MAXIMA_CLAVE} caracteres")
    if CARACTER_NUL in clave_en_claro:
        raise ClaveInsegura("contiene el caracter NUL")
