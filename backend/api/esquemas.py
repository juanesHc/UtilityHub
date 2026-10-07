from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, PlainSerializer


PATRON_TEXTO_SIN_CARACTER_NUL: str = r"^[^\x00]*$"


def marcar_como_utc(fecha_hora: datetime) -> datetime:
    return fecha_hora.replace(tzinfo=UTC) if fecha_hora.tzinfo is None else fecha_hora.astimezone(UTC)


FechaHoraUtc = Annotated[datetime, AfterValidator(marcar_como_utc)]
DecimalComoNumero = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class SolicitudInicioSesion(BaseModel):
    usuario: str = Field(min_length=1, max_length=50, pattern=PATRON_TEXTO_SIN_CARACTER_NUL)
    clave: str = Field(min_length=1, max_length=128, pattern=PATRON_TEXTO_SIN_CARACTER_NUL)


class TokenAccesoRespuesta(BaseModel):
    token_acceso: str
    tipo_token: Literal["bearer"]
    expira_en: FechaHoraUtc
    duracion_segundos: int


class ErrorRespuesta(BaseModel):
    detail: str


class LecturaHistoricoRespuesta(BaseModel):
    id_lectura: int
    codigo_torre: str
    nombre_torre: str
    numero_apartamento: str
    codigo_servicio: str
    nombre_servicio: str
    unidad_medida: str
    periodo: str
    lectura_acumulada: DecimalComoNumero
    consumo_periodo: DecimalComoNumero | None
    fecha_lectura: date
    promedio_referencia: DecimalComoNumero | None
    es_anomalo: bool


class PaginaHistoricoRespuesta(BaseModel):
    lecturas: list[LecturaHistoricoRespuesta]
    pagina: int
    tamano_pagina: int
    total_resultados: int
    total_paginas: int


class DetalleLecturaRespuesta(BaseModel):
    id_lectura: int
    id_carga: int
    codigo_torre: str
    nombre_torre: str
    numero_apartamento: str
    codigo_servicio: str
    nombre_servicio: str
    unidad_medida: str
    periodo: str
    fecha_lectura: date
    lectura_acumulada: DecimalComoNumero
    consumo_periodo: DecimalComoNumero | None
    promedio_referencia: DecimalComoNumero | None
    umbral_desviacion: DecimalComoNumero
    limite_inferior_normal: DecimalComoNumero | None
    limite_superior_normal: DecimalComoNumero | None
    desviacion_relativa: DecimalComoNumero | None
    fue_evaluada: bool
    es_anomalo: bool


class CargaRespuesta(BaseModel):
    id_carga: int
    codigo_torre: str
    nombre_torre: str
    periodo: str
    nombre_archivo: str
    fecha_procesamiento: FechaHoraUtc
    estado: str
    filas_aceptadas: int
    filas_rechazadas: int


class RechazoRespuesta(BaseModel):
    id_rechazo: int
    numero_fila: int
    apartamento: str | None
    servicio: str | None
    periodo: str | None
    motivo: str
    valor_recibido: str | None


class TorreRespuesta(BaseModel):
    id_torre: int
    codigo: str
    nombre: str


class SolicitudRegistroUsuario(BaseModel):
    usuario: str = Field(min_length=1, max_length=50, pattern=PATRON_TEXTO_SIN_CARACTER_NUL)
    clave: str = Field(min_length=1, max_length=128, pattern=PATRON_TEXTO_SIN_CARACTER_NUL)


class UsuarioRegistradoRespuesta(BaseModel):
    id_usuario: int
    nombre_usuario: str
    fecha_creacion: FechaHoraUtc
    creado_por: str | None


class AdministradorRespuesta(BaseModel):
    id_usuario: int
    nombre_usuario: str
    fecha_creacion: FechaHoraUtc | None
    creado_por: str | None
    ultimo_acceso: FechaHoraUtc | None
    esta_bloqueado: bool


class ServicioRespuesta(BaseModel):
    id_servicio: int
    codigo: str
    nombre: str
    unidad_medida: str
    umbral_desviacion: DecimalComoNumero
