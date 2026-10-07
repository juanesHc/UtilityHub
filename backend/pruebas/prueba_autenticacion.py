from datetime import datetime, timedelta

import jwt
import pytest

from api.servicio_autenticacion import (
    DURACION_BLOQUEO,
    DURACION_TOKEN,
    MAXIMO_INTENTOS_FALLIDOS,
    ServicioAutenticacion,
    calcular_estado_tras_intento_fallido,
    calcular_segundos_restantes,
    esta_bloqueado,
)
from comun.conexion import Conexion
from comun.excepciones import TokenInvalido
from comun.modelos import Usuario
from comun.reloj import obtener_fecha_hora_actual_utc


CLAVE_FIRMA_DE_PRUEBA: str = "clave-de-firma-de-la-prueba-unitaria-0123456789"
AHORA: datetime = datetime(2026, 10, 6, 12, 0, 0)


def conexion_no_permitida() -> Conexion:
    raise AssertionError("decodificar un token no debe tocar la base de datos")


def crear_servicio(clave_firma_token: str = CLAVE_FIRMA_DE_PRUEBA) -> ServicioAutenticacion:
    return ServicioAutenticacion(conexion_no_permitida, clave_firma_token)


def usuario(intentos_fallidos: int = 0, bloqueado_hasta: datetime | None = None) -> Usuario:
    return Usuario(
        id_usuario=1,
        nombre_usuario="admin",
        hash_contrasena="x",
        ultimo_acceso=None,
        intentos_fallidos=intentos_fallidos,
        bloqueado_hasta=bloqueado_hasta,
        version_credenciales=1,
    )


def prueba_token_recien_emitido_es_valido() -> None:
    servicio_autenticacion = crear_servicio()
    token_emitido = servicio_autenticacion.emitir_token("admin", 3, obtener_fecha_hora_actual_utc())
    reclamos = servicio_autenticacion.decodificar_token(token_emitido.token_acceso)
    assert (reclamos.nombre_usuario, reclamos.version_credenciales) == ("admin", 3)


def prueba_token_dura_ocho_horas() -> None:
    token_emitido = crear_servicio().emitir_token("admin", 1, AHORA)
    assert token_emitido.duracion_segundos == 8 * 3600
    assert token_emitido.fecha_expiracion.replace(tzinfo=None) == AHORA + timedelta(hours=8)


def prueba_token_a_un_minuto_de_vencer_sigue_siendo_valido() -> None:
    servicio_autenticacion = crear_servicio()
    fecha_inicio_sesion = obtener_fecha_hora_actual_utc() - DURACION_TOKEN + timedelta(minutes=1)
    token_emitido = servicio_autenticacion.emitir_token("admin", 1, fecha_inicio_sesion)
    assert servicio_autenticacion.decodificar_token(token_emitido.token_acceso).nombre_usuario == "admin"


def prueba_token_vencido_se_rechaza() -> None:
    servicio_autenticacion = crear_servicio()
    fecha_inicio_sesion = obtener_fecha_hora_actual_utc() - DURACION_TOKEN - timedelta(seconds=1)
    token_emitido = servicio_autenticacion.emitir_token("admin", 1, fecha_inicio_sesion)
    with pytest.raises(TokenInvalido):
        servicio_autenticacion.decodificar_token(token_emitido.token_acceso)


def prueba_token_firmado_con_otra_clave_se_rechaza() -> None:
    token_ajeno = crear_servicio("otra-clave-de-firma-distinta-0123456789-abcdef").emitir_token(
        "admin", 1, obtener_fecha_hora_actual_utc()
    )
    with pytest.raises(TokenInvalido):
        crear_servicio().decodificar_token(token_ajeno.token_acceso)


def prueba_token_con_contenido_alterado_se_rechaza() -> None:
    servicio_autenticacion = crear_servicio()
    token_acceso = servicio_autenticacion.emitir_token("admin", 1, obtener_fecha_hora_actual_utc()).token_acceso
    encabezado, _, firma = token_acceso.split(".")
    contenido_falso = jwt.encode(
        {"sub": "intruso"}, "clave-del-intruso-con-longitud-suficiente-0123", algorithm="HS256"
    ).split(".")[1]
    with pytest.raises(TokenInvalido):
        servicio_autenticacion.decodificar_token(f"{encabezado}.{contenido_falso}.{firma}")


def prueba_token_sin_firma_se_rechaza() -> None:
    ahora = obtener_fecha_hora_actual_utc()
    token_sin_firma = jwt.encode(
        {"sub": "admin", "ver": 1, "iat": ahora, "exp": ahora + timedelta(hours=1)},
        key=None,
        algorithm="none",
    )
    with pytest.raises(TokenInvalido):
        crear_servicio().decodificar_token(token_sin_firma)


@pytest.mark.parametrize(
    "reclamos_incompletos",
    [
        {"sub": "admin", "ver": 1, "iat": 0},
        {"sub": "admin", "iat": 0, "exp": 4102444800},
        {"sub": "admin", "ver": "1", "iat": 0, "exp": 4102444800},
        {"sub": "admin", "ver": True, "iat": 0, "exp": 4102444800},
    ],
)
def prueba_token_sin_vencimiento_o_sin_version_valida_se_rechaza(reclamos_incompletos: dict[str, object]) -> None:
    token_acceso = jwt.encode(reclamos_incompletos, CLAVE_FIRMA_DE_PRUEBA, algorithm="HS256")
    with pytest.raises(TokenInvalido):
        crear_servicio().decodificar_token(token_acceso)


@pytest.mark.parametrize("token_malformado", ["", "basura", "a.b.c"])
def prueba_token_malformado_se_rechaza(token_malformado: str) -> None:
    with pytest.raises(TokenInvalido):
        crear_servicio().decodificar_token(token_malformado)


def prueba_los_primeros_fallos_solo_suman() -> None:
    estado_bloqueo = calcular_estado_tras_intento_fallido(usuario(intentos_fallidos=MAXIMO_INTENTOS_FALLIDOS - 2), AHORA)
    assert estado_bloqueo.intentos_fallidos == MAXIMO_INTENTOS_FALLIDOS - 1
    assert estado_bloqueo.bloqueado_hasta is None


def prueba_el_quinto_fallo_bloquea_quince_minutos() -> None:
    estado_bloqueo = calcular_estado_tras_intento_fallido(usuario(intentos_fallidos=MAXIMO_INTENTOS_FALLIDOS - 1), AHORA)
    assert estado_bloqueo.intentos_fallidos == MAXIMO_INTENTOS_FALLIDOS
    assert estado_bloqueo.bloqueado_hasta == AHORA + DURACION_BLOQUEO
    assert MAXIMO_INTENTOS_FALLIDOS == 5
    assert DURACION_BLOQUEO == timedelta(minutes=15)


def prueba_tras_un_bloqueo_vencido_el_contador_empieza_de_nuevo() -> None:
    usuario_con_bloqueo_vencido = usuario(intentos_fallidos=MAXIMO_INTENTOS_FALLIDOS, bloqueado_hasta=AHORA - timedelta(seconds=1))
    assert not esta_bloqueado(usuario_con_bloqueo_vencido, AHORA)
    estado_bloqueo = calcular_estado_tras_intento_fallido(usuario_con_bloqueo_vencido, AHORA)
    assert (estado_bloqueo.intentos_fallidos, estado_bloqueo.bloqueado_hasta) == (1, None)


def prueba_bloqueo_vigente_hasta_su_ultimo_segundo() -> None:
    assert esta_bloqueado(usuario(bloqueado_hasta=AHORA + timedelta(seconds=1)), AHORA)
    assert not esta_bloqueado(usuario(bloqueado_hasta=AHORA), AHORA)
    assert not esta_bloqueado(usuario(), AHORA)


def prueba_segundos_restantes_se_redondean_hacia_arriba() -> None:
    assert calcular_segundos_restantes(AHORA + timedelta(seconds=90, milliseconds=1), AHORA) == 91
    assert calcular_segundos_restantes(AHORA, AHORA) == 1
