import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Self

from comun.excepciones import PeriodoInvalido, RangoDePeriodosInvalido


PATRON_PERIODO: re.Pattern[str] = re.compile(r"([0-9]{4})-([0-9]{2})")


@dataclass(frozen=True)
class FilaCruda:
    numero_linea: int
    torre: str
    apartamento: str
    servicio: str
    periodo: str
    lectura_acumulada: str
    fecha_lectura: str
    celdas_sobrantes: tuple[str, ...]


@dataclass(frozen=True, order=True)
class Periodo:
    anio: int
    mes: int

    def __post_init__(self) -> None:
        if not 1 <= self.mes <= 12:
            raise PeriodoInvalido(f"{self.anio:04d}-{self.mes:02d}")

    @classmethod
    def desde_texto(cls, texto_periodo: str) -> Self:
        coincidencia = PATRON_PERIODO.fullmatch(texto_periodo)
        if coincidencia is None:
            raise PeriodoInvalido(texto_periodo)
        return cls(anio=int(coincidencia.group(1)), mes=int(coincidencia.group(2)))

    def anterior(self) -> Self:
        if self.mes == 1:
            return type(self)(anio=self.anio - 1, mes=12)
        return type(self)(anio=self.anio, mes=self.mes - 1)

    def como_texto(self) -> str:
        return f"{self.anio:04d}-{self.mes:02d}"


class EstadoCarga(Enum):
    PROCESADA_COMPLETA = "procesada_completa"
    PROCESADA_PARCIAL = "procesada_parcial"
    RECHAZADA = "rechazada"
    REEMPLAZADA = "reemplazada"


class MotivoRechazo(Enum):
    COLUMNAS_SOBRANTES = "columnas_sobrantes"
    CAMPO_OBLIGATORIO_FALTANTE = "campo_obligatorio_faltante"
    TRIPLETA_REPETIDA_EN_ARCHIVO = "tripleta_repetida_en_archivo"
    TORRE_DISTINTA_A_LA_DEL_ARCHIVO = "torre_distinta_a_la_del_archivo"
    PERIODO_DISTINTO_AL_DEL_ARCHIVO = "periodo_distinto_al_del_archivo"
    LECTURA_NO_NUMERICA = "lectura_no_numerica"
    LECTURA_FUERA_DE_RANGO = "lectura_fuera_de_rango"
    FECHA_LECTURA_INVALIDA = "fecha_lectura_invalida"
    APARTAMENTO_INEXISTENTE = "apartamento_inexistente"
    SERVICIO_INEXISTENTE = "servicio_inexistente"
    LECTURA_MENOR_QUE_LA_ANTERIOR = "lectura_menor_que_la_anterior"


@dataclass(frozen=True)
class IdentificacionArchivo:
    codigo_torre: str
    periodo: Periodo


@dataclass(frozen=True)
class Torre:
    id_torre: int
    codigo: str
    nombre: str


@dataclass(frozen=True)
class Apartamento:
    id_apartamento: int
    id_torre: int
    numero: str


@dataclass(frozen=True)
class Servicio:
    id_servicio: int
    codigo: str
    nombre: str
    unidad_medida: str
    umbral_desviacion: Decimal


@dataclass(frozen=True)
class CargaRegistrada:
    id_carga: int
    id_torre: int
    nombre_archivo: str
    periodo: Periodo
    fecha_procesamiento: datetime
    estado: EstadoCarga


@dataclass(frozen=True)
class LecturaHistorica:
    id_apartamento: int
    id_servicio: int
    periodo: Periodo
    lectura_acumulada: Decimal
    consumo_periodo: Decimal | None
    es_anomalo: bool


@dataclass(frozen=True)
class LecturaValidada:
    numero_linea: int
    apartamento: Apartamento
    servicio: Servicio
    periodo: Periodo
    lectura_acumulada: Decimal
    fecha_lectura: date


@dataclass(frozen=True)
class LecturaEvaluada:
    lectura_validada: LecturaValidada
    consumo_periodo: Decimal | None
    promedio_referencia: Decimal | None
    es_anomalo: bool


@dataclass(frozen=True)
class FilaRechazada:
    fila_cruda: FilaCruda
    motivo_rechazo: MotivoRechazo
    valor_recibido: str | None
    detalle_rechazo: str


@dataclass(frozen=True)
class ResultadoValidacion:
    lecturas_validadas: tuple[LecturaValidada, ...]
    filas_rechazadas: tuple[FilaRechazada, ...]


@dataclass(frozen=True)
class ResultadoProcesamiento:
    id_carga: int
    nombre_archivo: str
    codigo_torre: str
    periodo: Periodo
    fecha_procesamiento: datetime
    estado_carga: EstadoCarga
    lecturas_aceptadas: tuple[LecturaEvaluada, ...]
    filas_rechazadas: tuple[FilaRechazada, ...]
    ids_cargas_reemplazadas: tuple[int, ...]


@dataclass(frozen=True)
class Usuario:
    id_usuario: int
    nombre_usuario: str
    hash_contrasena: str = field(repr=False)
    ultimo_acceso: datetime | None
    intentos_fallidos: int
    bloqueado_hasta: datetime | None
    version_credenciales: int


@dataclass(frozen=True)
class UsuarioRegistrado:
    id_usuario: int
    nombre_usuario: str
    fecha_creacion: datetime
    nombre_usuario_creador: str | None


@dataclass(frozen=True)
class FiltrosHistoricoLecturas:
    codigo_torre: str | None
    numero_apartamento: str | None
    codigo_servicio: str | None
    periodo_desde: Periodo | None
    periodo_hasta: Periodo | None
    solo_anomalos: bool

    def __post_init__(self) -> None:
        if (
            self.periodo_desde is not None
            and self.periodo_hasta is not None
            and self.periodo_desde > self.periodo_hasta
        ):
            raise RangoDePeriodosInvalido(self.periodo_desde.como_texto(), self.periodo_hasta.como_texto())


@dataclass(frozen=True)
class SolicitudPagina:
    numero_pagina: int
    tamano_pagina: int

    @property
    def cantidad_a_omitir(self) -> int:
        return (self.numero_pagina - 1) * self.tamano_pagina


@dataclass(frozen=True)
class LecturaConsultada:
    id_lectura: int
    id_carga: int
    codigo_torre: str
    nombre_torre: str
    numero_apartamento: str
    codigo_servicio: str
    nombre_servicio: str
    unidad_medida: str
    umbral_desviacion: Decimal
    periodo: Periodo
    lectura_acumulada: Decimal
    consumo_periodo: Decimal | None
    fecha_lectura: date
    promedio_referencia: Decimal | None
    es_anomalo: bool


@dataclass(frozen=True)
class PaginaLecturas:
    lecturas: tuple[LecturaConsultada, ...]
    total_resultados: int
    solicitud_pagina: SolicitudPagina

    @property
    def total_paginas(self) -> int:
        return math.ceil(self.total_resultados / self.solicitud_pagina.tamano_pagina)


@dataclass(frozen=True)
class RangoConsumoNormal:
    limite_inferior: Decimal
    limite_superior: Decimal


@dataclass(frozen=True)
class DetalleLecturaExplicada:
    lectura: LecturaConsultada
    rango_consumo_normal: RangoConsumoNormal | None
    desviacion_relativa: Decimal | None


@dataclass(frozen=True)
class ResumenCarga:
    id_carga: int
    codigo_torre: str
    nombre_torre: str
    periodo: Periodo
    nombre_archivo: str
    fecha_procesamiento: datetime
    estado: EstadoCarga
    cantidad_lecturas_aceptadas: int
    cantidad_filas_rechazadas: int


@dataclass(frozen=True)
class RechazoRegistrado:
    id_rechazo: int
    id_carga: int
    numero_fila: int
    apartamento: str | None
    servicio: str | None
    periodo: str | None
    motivo_rechazo: MotivoRechazo
    valor_recibido: str | None


@dataclass(frozen=True)
class UsuarioListado:
    id_usuario: int
    nombre_usuario: str
    fecha_creacion: datetime | None
    nombre_usuario_creador: str | None
    ultimo_acceso: datetime | None
    bloqueado_hasta: datetime | None


class EstadoSubida(Enum):
    PENDIENTE = "pendiente"
    PROCESADA = "procesada"
    FALLIDA = "fallida"


@dataclass(frozen=True)
class SubidaRegistrada:
    id_subida: int
    clave_objeto: str
    nombre_archivo: str
    fecha_solicitud: datetime
    estado: EstadoSubida
    id_carga: int | None
    detalle_error: str | None
    fecha_procesamiento: datetime | None
