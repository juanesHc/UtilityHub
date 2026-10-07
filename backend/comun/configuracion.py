import os
from dataclasses import dataclass, field

from comun.excepciones import ConfiguracionIncompleta, ConfiguracionInvalida


VARIABLE_HOST: str = "UTILITYHUB_DB_HOST"
VARIABLE_PUERTO: str = "UTILITYHUB_DB_PUERTO"
VARIABLE_USUARIO: str = "UTILITYHUB_DB_USUARIO"
VARIABLE_CLAVE: str = "UTILITYHUB_DB_CLAVE"
VARIABLE_NOMBRE_BASE_DATOS: str = "UTILITYHUB_DB_NOMBRE"

PUERTO_POSTGRESQL_POR_DEFECTO: int = 5432


@dataclass(frozen=True)
class ConfiguracionBaseDatos:
    host: str
    puerto: int
    usuario: str
    clave: str = field(repr=False)
    nombre_base_datos: str


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
    )


def leer_puerto_desde_entorno() -> int:
    texto_puerto = os.environ.get(VARIABLE_PUERTO)
    if texto_puerto is None or texto_puerto.strip() == "":
        return PUERTO_POSTGRESQL_POR_DEFECTO
    if not texto_puerto.strip().isdigit():
        raise ConfiguracionInvalida(VARIABLE_PUERTO, texto_puerto)
    return int(texto_puerto.strip())
