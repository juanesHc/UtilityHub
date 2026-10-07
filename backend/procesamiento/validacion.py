import re
from collections import Counter
from datetime import date
from decimal import Decimal

from comun.modelos import (
    Apartamento,
    FilaCruda,
    FilaRechazada,
    LecturaHistorica,
    LecturaValidada,
    MotivoRechazo,
    Periodo,
    ResultadoValidacion,
    Servicio,
    Torre,
)
from procesamiento.calculo import PRECISION_ALMACENADA, agrupar_historial_por_apartamento_y_servicio


CAMPOS_OBLIGATORIOS: tuple[str, ...] = (
    "torre",
    "apartamento",
    "servicio",
    "periodo",
    "lectura_acumulada",
    "fecha_lectura",
)
PATRON_LECTURA_NUMERICA: re.Pattern[str] = re.compile(r"-?[0-9]+(\.[0-9]+)?")
PATRON_FECHA_ISO: re.Pattern[str] = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
LECTURA_ACUMULADA_MAXIMA_EXCLUSIVA: Decimal = Decimal("100000000000")


class ValidadorFilas:
    def __init__(
        self,
        torre: Torre,
        periodo_archivo: Periodo,
        apartamentos_de_la_torre: tuple[Apartamento, ...],
        servicios: tuple[Servicio, ...],
        historial: tuple[LecturaHistorica, ...],
    ) -> None:
        self.torre: Torre = torre
        self.periodo_archivo: Periodo = periodo_archivo
        self.apartamento_por_numero: dict[str, Apartamento] = {
            apartamento.numero: apartamento for apartamento in apartamentos_de_la_torre
        }
        self.servicio_por_codigo: dict[str, Servicio] = {servicio.codigo: servicio for servicio in servicios}
        self.ultima_lectura_por_apartamento_y_servicio: dict[tuple[int, int], LecturaHistorica] = {
            clave: lecturas[-1]
            for clave, lecturas in agrupar_historial_por_apartamento_y_servicio(historial).items()
        }

    def validar_filas(self, filas_crudas: tuple[FilaCruda, ...]) -> ResultadoValidacion:
        tripletas_repetidas = encontrar_tripletas_repetidas(filas_crudas)
        lecturas_validadas: list[LecturaValidada] = []
        filas_rechazadas: list[FilaRechazada] = []
        for fila_cruda in filas_crudas:
            resultado_fila = self.validar_fila(fila_cruda, tripletas_repetidas)
            if isinstance(resultado_fila, FilaRechazada):
                filas_rechazadas.append(resultado_fila)
            else:
                lecturas_validadas.append(resultado_fila)
        return ResultadoValidacion(
            lecturas_validadas=tuple(lecturas_validadas),
            filas_rechazadas=tuple(filas_rechazadas),
        )

    def validar_fila(
        self,
        fila_cruda: FilaCruda,
        tripletas_repetidas: frozenset[tuple[str, str, str]],
    ) -> LecturaValidada | FilaRechazada:
        if fila_cruda.celdas_sobrantes:
            return FilaRechazada(
                fila_cruda=fila_cruda,
                motivo_rechazo=MotivoRechazo.COLUMNAS_SOBRANTES,
                valor_recibido=", ".join(fila_cruda.celdas_sobrantes),
                detalle_rechazo="valores sin columna: " + ", ".join(fila_cruda.celdas_sobrantes),
            )

        campos_faltantes = [campo for campo in CAMPOS_OBLIGATORIOS if getattr(fila_cruda, campo) == ""]
        if campos_faltantes:
            return FilaRechazada(
                fila_cruda=fila_cruda,
                motivo_rechazo=MotivoRechazo.CAMPO_OBLIGATORIO_FALTANTE,
                valor_recibido=None,
                detalle_rechazo="campos vacíos: " + ", ".join(campos_faltantes),
            )

        if tripleta_de_la_fila(fila_cruda) in tripletas_repetidas:
            return FilaRechazada(
                fila_cruda=fila_cruda,
                motivo_rechazo=MotivoRechazo.TRIPLETA_REPETIDA_EN_ARCHIVO,
                valor_recibido=fila_cruda.lectura_acumulada,
                detalle_rechazo=(
                    f"apartamento {fila_cruda.apartamento}, servicio {fila_cruda.servicio} y periodo "
                    f"{fila_cruda.periodo} aparecen más de una vez en el archivo"
                ),
            )

        if fila_cruda.torre != self.torre.codigo:
            return FilaRechazada(
                fila_cruda=fila_cruda,
                motivo_rechazo=MotivoRechazo.TORRE_DISTINTA_A_LA_DEL_ARCHIVO,
                valor_recibido=fila_cruda.torre,
                detalle_rechazo=f"la fila dice {fila_cruda.torre} y el archivo es de {self.torre.codigo}",
            )

        if fila_cruda.periodo != self.periodo_archivo.como_texto():
            return FilaRechazada(
                fila_cruda=fila_cruda,
                motivo_rechazo=MotivoRechazo.PERIODO_DISTINTO_AL_DEL_ARCHIVO,
                valor_recibido=fila_cruda.periodo,
                detalle_rechazo=f"la fila dice {fila_cruda.periodo} y el archivo es de {self.periodo_archivo.como_texto()}",
            )

        if PATRON_LECTURA_NUMERICA.fullmatch(fila_cruda.lectura_acumulada) is None:
            return FilaRechazada(
                fila_cruda=fila_cruda,
                motivo_rechazo=MotivoRechazo.LECTURA_NO_NUMERICA,
                valor_recibido=fila_cruda.lectura_acumulada,
                detalle_rechazo=f"valor recibido: {fila_cruda.lectura_acumulada}",
            )

        lectura_acumulada = Decimal(fila_cruda.lectura_acumulada)
        if not lectura_dentro_de_rango(lectura_acumulada):
            return FilaRechazada(
                fila_cruda=fila_cruda,
                motivo_rechazo=MotivoRechazo.LECTURA_FUERA_DE_RANGO,
                valor_recibido=fila_cruda.lectura_acumulada,
                detalle_rechazo=(
                    f"debe ser mayor o igual a 0, menor que {LECTURA_ACUMULADA_MAXIMA_EXCLUSIVA} "
                    f"y con máximo 3 decimales; valor recibido: {fila_cruda.lectura_acumulada}"
                ),
            )

        fecha_lectura = interpretar_fecha_iso(fila_cruda.fecha_lectura)
        if fecha_lectura is None:
            return FilaRechazada(
                fila_cruda=fila_cruda,
                motivo_rechazo=MotivoRechazo.FECHA_LECTURA_INVALIDA,
                valor_recibido=fila_cruda.fecha_lectura,
                detalle_rechazo=f"se espera AAAA-MM-DD; valor recibido: {fila_cruda.fecha_lectura}",
            )

        apartamento = self.apartamento_por_numero.get(fila_cruda.apartamento)
        if apartamento is None:
            return FilaRechazada(
                fila_cruda=fila_cruda,
                motivo_rechazo=MotivoRechazo.APARTAMENTO_INEXISTENTE,
                valor_recibido=fila_cruda.apartamento,
                detalle_rechazo=f"el apartamento {fila_cruda.apartamento} no existe en la torre {self.torre.codigo}",
            )

        servicio = self.servicio_por_codigo.get(fila_cruda.servicio)
        if servicio is None:
            return FilaRechazada(
                fila_cruda=fila_cruda,
                motivo_rechazo=MotivoRechazo.SERVICIO_INEXISTENTE,
                valor_recibido=fila_cruda.servicio,
                detalle_rechazo=f"el servicio {fila_cruda.servicio} no existe",
            )

        lectura_anterior = self.ultima_lectura_por_apartamento_y_servicio.get(
            (apartamento.id_apartamento, servicio.id_servicio)
        )
        if lectura_anterior is not None and lectura_acumulada < lectura_anterior.lectura_acumulada:
            return FilaRechazada(
                fila_cruda=fila_cruda,
                motivo_rechazo=MotivoRechazo.LECTURA_MENOR_QUE_LA_ANTERIOR,
                valor_recibido=fila_cruda.lectura_acumulada,
                detalle_rechazo=(
                    f"lectura {lectura_acumulada} menor que {lectura_anterior.lectura_acumulada} "
                    f"del periodo {lectura_anterior.periodo.como_texto()}"
                ),
            )

        return LecturaValidada(
            numero_linea=fila_cruda.numero_linea,
            apartamento=apartamento,
            servicio=servicio,
            periodo=self.periodo_archivo,
            lectura_acumulada=lectura_acumulada,
            fecha_lectura=fecha_lectura,
        )


def tripleta_de_la_fila(fila_cruda: FilaCruda) -> tuple[str, str, str]:
    return (fila_cruda.apartamento, fila_cruda.servicio, fila_cruda.periodo)


def encontrar_tripletas_repetidas(filas_crudas: tuple[FilaCruda, ...]) -> frozenset[tuple[str, str, str]]:
    apariciones_por_tripleta = Counter(
        tripleta_de_la_fila(fila_cruda)
        for fila_cruda in filas_crudas
        if fila_cruda.apartamento and fila_cruda.servicio and fila_cruda.periodo
    )
    return frozenset(tripleta for tripleta, apariciones in apariciones_por_tripleta.items() if apariciones > 1)


def lectura_dentro_de_rango(lectura_acumulada: Decimal) -> bool:
    if lectura_acumulada < 0 or lectura_acumulada >= LECTURA_ACUMULADA_MAXIMA_EXCLUSIVA:
        return False
    return lectura_acumulada == lectura_acumulada.quantize(PRECISION_ALMACENADA)


def interpretar_fecha_iso(texto_fecha: str) -> date | None:
    if PATRON_FECHA_ISO.fullmatch(texto_fecha) is None:
        return None
    try:
        return date.fromisoformat(texto_fecha)
    except ValueError:
        return None
