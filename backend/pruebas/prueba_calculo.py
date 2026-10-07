from datetime import date
from decimal import Decimal

import pytest

from comun.modelos import Apartamento, EstadoCarga, LecturaHistorica, LecturaValidada, Periodo, Servicio
from procesamiento.calculo import (
    calcular_desviacion_relativa,
    calcular_rango_consumo_normal,
    determinar_estado_carga,
    evaluar_lectura,
    supera_umbral_de_desviacion,
)


AGUA: Servicio = Servicio(id_servicio=1, codigo="AGUA", nombre="Agua", unidad_medida="m3", umbral_desviacion=Decimal("0.50"))
APARTAMENTO: Apartamento = Apartamento(id_apartamento=10, id_torre=1, numero="101")


def lectura_validada(periodo: Periodo, lectura_acumulada: str) -> LecturaValidada:
    return LecturaValidada(2, APARTAMENTO, AGUA, periodo, Decimal(lectura_acumulada), date(2026, 1, 1))


def historica(periodo: Periodo, lectura_acumulada: str, consumo_periodo: str | None, es_anomalo: bool = False) -> LecturaHistorica:
    return LecturaHistorica(
        id_apartamento=10,
        id_servicio=1,
        periodo=periodo,
        lectura_acumulada=Decimal(lectura_acumulada),
        consumo_periodo=None if consumo_periodo is None else Decimal(consumo_periodo),
        es_anomalo=es_anomalo,
    )


def prueba_linea_base_sin_historial() -> None:
    lectura_evaluada = evaluar_lectura(lectura_validada(Periodo(2025, 10), "500"), ())
    assert lectura_evaluada.consumo_periodo is None
    assert lectura_evaluada.promedio_referencia is None
    assert lectura_evaluada.es_anomalo is False


def prueba_segundo_periodo_tiene_consumo_pero_no_se_evalua() -> None:
    historial = (historica(Periodo(2025, 10), "500", None),)
    lectura_evaluada = evaluar_lectura(lectura_validada(Periodo(2025, 11), "510"), historial)
    assert lectura_evaluada.consumo_periodo == Decimal("10")
    assert lectura_evaluada.promedio_referencia is None
    assert lectura_evaluada.es_anomalo is False


def prueba_hueco_en_el_periodo_anterior_deja_consumo_nulo() -> None:
    historial = (historica(Periodo(2025, 10), "500", None), historica(Periodo(2025, 11), "510", "10"))
    lectura_evaluada = evaluar_lectura(lectura_validada(Periodo(2026, 1), "530"), historial)
    assert lectura_evaluada.consumo_periodo is None
    assert lectura_evaluada.es_anomalo is False


def prueba_promedio_excluye_consumos_anomalos_y_se_redondea() -> None:
    historial = (
        historica(Periodo(2025, 10), "500", None),
        historica(Periodo(2025, 11), "510", "10"),
        historica(Periodo(2025, 12), "550", "40", es_anomalo=True),
        historica(Periodo(2026, 1), "561", "11"),
        historica(Periodo(2026, 2), "571", "10"),
    )
    lectura_evaluada = evaluar_lectura(lectura_validada(Periodo(2026, 3), "601"), historial)
    assert lectura_evaluada.promedio_referencia == Decimal("10.333")
    assert lectura_evaluada.consumo_periodo == Decimal("30")
    assert lectura_evaluada.es_anomalo is True


@pytest.mark.parametrize(
    ("consumo_periodo", "es_anomalo_esperado"),
    [("4.124", True), ("4.125", False), ("8.25", False), ("12.375", False), ("12.376", True)],
)
def prueba_limites_exactos_del_umbral(consumo_periodo: str, es_anomalo_esperado: bool) -> None:
    assert supera_umbral_de_desviacion(Decimal(consumo_periodo), Decimal("8.250"), Decimal("0.50")) is es_anomalo_esperado


def prueba_rango_normal_no_baja_de_cero() -> None:
    rango_consumo_normal = calcular_rango_consumo_normal(Decimal("10"), Decimal("1.5"))
    assert rango_consumo_normal.limite_inferior == Decimal("0")
    assert rango_consumo_normal.limite_superior == Decimal("25.0")


def prueba_desviacion_relativa() -> None:
    assert calcular_desviacion_relativa(Decimal("26.3"), Decimal("8.250")) == Decimal("2.1879")
    assert calcular_desviacion_relativa(Decimal("5"), Decimal("0")) is None


@pytest.mark.parametrize(
    ("aceptadas", "rechazadas", "estado_esperado"),
    [(40, 0, EstadoCarga.PROCESADA_COMPLETA), (39, 1, EstadoCarga.PROCESADA_PARCIAL), (0, 5, EstadoCarga.RECHAZADA), (0, 0, EstadoCarga.RECHAZADA)],
)
def prueba_estado_de_la_carga(aceptadas: int, rechazadas: int, estado_esperado: EstadoCarga) -> None:
    assert determinar_estado_carga(aceptadas, rechazadas) == estado_esperado
