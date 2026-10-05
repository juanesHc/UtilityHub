from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from operator import attrgetter

from comun.modelos import EstadoCarga, LecturaEvaluada, LecturaHistorica, LecturaValidada, RangoConsumoNormal


PRECISION_ALMACENADA: Decimal = Decimal("0.001")
PRECISION_DESVIACION_RELATIVA: Decimal = Decimal("0.0001")


def agrupar_historial_por_apartamento_y_servicio(
    historial: tuple[LecturaHistorica, ...],
) -> dict[tuple[int, int], tuple[LecturaHistorica, ...]]:
    historial_agrupado: defaultdict[tuple[int, int], list[LecturaHistorica]] = defaultdict(list)
    for lectura_historica in sorted(historial, key=attrgetter("periodo")):
        clave = (lectura_historica.id_apartamento, lectura_historica.id_servicio)
        historial_agrupado[clave].append(lectura_historica)
    return {clave: tuple(lecturas) for clave, lecturas in historial_agrupado.items()}


def evaluar_lecturas(
    lecturas_validadas: tuple[LecturaValidada, ...],
    historial: tuple[LecturaHistorica, ...],
) -> tuple[LecturaEvaluada, ...]:
    historial_por_clave = agrupar_historial_por_apartamento_y_servicio(historial)
    return tuple(
        evaluar_lectura(
            lectura_validada,
            historial_por_clave.get(
                (lectura_validada.apartamento.id_apartamento, lectura_validada.servicio.id_servicio),
                (),
            ),
        )
        for lectura_validada in lecturas_validadas
    )


def evaluar_lectura(
    lectura_validada: LecturaValidada,
    historial_del_apartamento_y_servicio: tuple[LecturaHistorica, ...],
) -> LecturaEvaluada:
    consumo_periodo = calcular_consumo_periodo(lectura_validada, historial_del_apartamento_y_servicio)
    if consumo_periodo is None:
        return LecturaEvaluada(lectura_validada, consumo_periodo=None, promedio_referencia=None, es_anomalo=False)

    promedio_referencia = calcular_promedio_referencia(historial_del_apartamento_y_servicio)
    if promedio_referencia is None:
        return LecturaEvaluada(lectura_validada, consumo_periodo, promedio_referencia=None, es_anomalo=False)

    es_anomalo = supera_umbral_de_desviacion(
        consumo_periodo,
        promedio_referencia,
        lectura_validada.servicio.umbral_desviacion,
    )
    return LecturaEvaluada(lectura_validada, consumo_periodo, promedio_referencia, es_anomalo)


def calcular_consumo_periodo(
    lectura_validada: LecturaValidada,
    historial_del_apartamento_y_servicio: tuple[LecturaHistorica, ...],
) -> Decimal | None:
    if not historial_del_apartamento_y_servicio:
        return None
    lectura_anterior = historial_del_apartamento_y_servicio[-1]
    if lectura_anterior.periodo != lectura_validada.periodo.anterior():
        return None
    return lectura_validada.lectura_acumulada - lectura_anterior.lectura_acumulada


def calcular_promedio_referencia(historial_del_apartamento_y_servicio: tuple[LecturaHistorica, ...]) -> Decimal | None:
    consumos_no_anomalos = [
        lectura_historica.consumo_periodo
        for lectura_historica in historial_del_apartamento_y_servicio
        if lectura_historica.consumo_periodo is not None and not lectura_historica.es_anomalo
    ]
    if not consumos_no_anomalos:
        return None
    promedio = sum(consumos_no_anomalos, Decimal(0)) / len(consumos_no_anomalos)
    return promedio.quantize(PRECISION_ALMACENADA, rounding=ROUND_HALF_UP)


def calcular_rango_consumo_normal(promedio_referencia: Decimal, umbral_desviacion: Decimal) -> RangoConsumoNormal:
    desviacion_tolerada = promedio_referencia * umbral_desviacion
    return RangoConsumoNormal(
        limite_inferior=max(Decimal(0), promedio_referencia - desviacion_tolerada),
        limite_superior=promedio_referencia + desviacion_tolerada,
    )


def supera_umbral_de_desviacion(
    consumo_periodo: Decimal,
    promedio_referencia: Decimal,
    umbral_desviacion: Decimal,
) -> bool:
    rango_consumo_normal = calcular_rango_consumo_normal(promedio_referencia, umbral_desviacion)
    return (
        consumo_periodo < rango_consumo_normal.limite_inferior
        or consumo_periodo > rango_consumo_normal.limite_superior
    )


def calcular_desviacion_relativa(consumo_periodo: Decimal, promedio_referencia: Decimal) -> Decimal | None:
    if promedio_referencia == 0:
        return None
    return ((consumo_periodo - promedio_referencia) / promedio_referencia).quantize(
        PRECISION_DESVIACION_RELATIVA,
        rounding=ROUND_HALF_UP,
    )


def determinar_estado_carga(cantidad_lecturas_aceptadas: int, cantidad_filas_rechazadas: int) -> EstadoCarga:
    if cantidad_lecturas_aceptadas == 0:
        return EstadoCarga.RECHAZADA
    if cantidad_filas_rechazadas == 0:
        return EstadoCarga.PROCESADA_COMPLETA
    return EstadoCarga.PROCESADA_PARCIAL
