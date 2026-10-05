import os
from dataclasses import dataclass, field

from comun.excepciones import ConfiguracionIncompleta, ConfiguracionInvalida


VARIABLE_CLAVE_FIRMA_TOKEN: str = "UTILITYHUB_JWT_CLAVE_FIRMA"
VARIABLE_ORIGENES_CORS: str = "UTILITYHUB_CORS_ORIGENES"
LONGITUD_MINIMA_CLAVE_FIRMA: int = 32


@dataclass(frozen=True)
class ConfiguracionApi:
    clave_firma_token: str = field(repr=False)
    origenes_cors_permitidos: tuple[str, ...]


def cargar_configuracion_api_desde_entorno() -> ConfiguracionApi:
    variables_faltantes = tuple(
        nombre
        for nombre in (VARIABLE_CLAVE_FIRMA_TOKEN, VARIABLE_ORIGENES_CORS)
        if not os.environ.get(nombre, "").strip()
    )
    if variables_faltantes:
        raise ConfiguracionIncompleta(variables_faltantes)

    clave_firma_token = os.environ[VARIABLE_CLAVE_FIRMA_TOKEN]
    if len(clave_firma_token.encode("utf-8")) < LONGITUD_MINIMA_CLAVE_FIRMA:
        raise ConfiguracionInvalida(VARIABLE_CLAVE_FIRMA_TOKEN, f"menos de {LONGITUD_MINIMA_CLAVE_FIRMA} bytes")

    origenes_cors_permitidos = tuple(
        origen.strip().rstrip("/")
        for origen in os.environ[VARIABLE_ORIGENES_CORS].split(",")
        if origen.strip()
    )
    return ConfiguracionApi(
        clave_firma_token=clave_firma_token,
        origenes_cors_permitidos=origenes_cors_permitidos,
    )
