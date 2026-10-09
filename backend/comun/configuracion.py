import os
from dataclasses import dataclass, field

from comun.excepciones import ConfiguracionIncompleta, ConfiguracionInvalida


VARIABLE_HOST: str = "UTILITYHUB_DB_HOST"
VARIABLE_PUERTO: str = "UTILITYHUB_DB_PUERTO"
VARIABLE_USUARIO: str = "UTILITYHUB_DB_USUARIO"
VARIABLE_CLAVE: str = "UTILITYHUB_DB_CLAVE"
VARIABLE_NOMBRE_BASE_DATOS: str = "UTILITYHUB_DB_NOMBRE"
VARIABLE_MODO_SSL: str = "UTILITYHUB_DB_MODO_SSL"

PUERTO_POSTGRESQL_POR_DEFECTO: int = 5432
MODO_SSL_POR_DEFECTO: str = "prefer"
MODOS_SSL_ADMITIDOS: tuple[str, ...] = ("disable", "prefer", "require")


@dataclass(frozen=True)
class ConfiguracionBaseDatos:
    host: str
    puerto: int
    usuario: str
    clave: str = field(repr=False)
    nombre_base_datos: str
    modo_ssl: str = MODO_SSL_POR_DEFECTO


def cargar_configuracion_desde_entorno() -> ConfiguracionBaseDatos:
    variables_obligatorias = (VARIABLE_HOST, VARIABLE_USUARIO, VARIABLE_CLAVE, VARIABLE_NOMBRE_BASE_DATOS)
    variables_faltantes = tuple(nombre for nombre in variables_obligatorias if os.environ.get(nombre) is None)
    if variables_faltantes:
        raise ConfiguracionIncompleta(variables_faltantes)

    return ConfiguracionBaseDatos(
        host=os.environ[VARIABLE_HOST],
        puerto=leer_puerto_desde_entorno(),
        usuario=os.environ[VARIABLE_USUARIO],
        clave=os.environ[VARIABLE_CLAVE],
        nombre_base_datos=os.environ[VARIABLE_NOMBRE_BASE_DATOS],
        modo_ssl=leer_modo_ssl_desde_entorno(),
    )


def leer_modo_ssl_desde_entorno() -> str:
    texto_modo_ssl = os.environ.get(VARIABLE_MODO_SSL, "").strip()
    if texto_modo_ssl == "":
        return MODO_SSL_POR_DEFECTO
    if texto_modo_ssl not in MODOS_SSL_ADMITIDOS:
        raise ConfiguracionInvalida(VARIABLE_MODO_SSL, texto_modo_ssl)
    return texto_modo_ssl


def leer_puerto_desde_entorno() -> int:
    texto_puerto = os.environ.get(VARIABLE_PUERTO)
    if texto_puerto is None or texto_puerto.strip() == "":
        return PUERTO_POSTGRESQL_POR_DEFECTO
    if not texto_puerto.strip().isdigit():
        raise ConfiguracionInvalida(VARIABLE_PUERTO, texto_puerto)
    return int(texto_puerto.strip())
