from datetime import date
from decimal import Decimal

import pytest

from comun.modelos import (
    Apartamento,
    FilaCruda,
    FilaRechazada,
    LecturaHistorica,
    LecturaValidada,
    MotivoRechazo,
    Periodo,
    Servicio,
    Torre,
)
from procesamiento.validacion import ValidadorFilas


TORRE: Torre = Torre(id_torre=1, codigo="T01", nombre="Torre 1")
APARTAMENTO_101: Apartamento = Apartamento(id_apartamento=10, id_torre=1, numero="101")
APARTAMENTO_102: Apartamento = Apartamento(id_apartamento=11, id_torre=1, numero="102")
AGUA: Servicio = Servicio(id_servicio=1, codigo="AGUA", nombre="Agua", unidad_medida="m3", umbral_desviacion=Decimal("0.50"))
PERIODO_ARCHIVO: Periodo = Periodo(2026, 3)
LECTURA_ANTERIOR_101: LecturaHistorica = LecturaHistorica(
    id_apartamento=10,
    id_servicio=1,
    periodo=Periodo(2026, 2),
    lectura_acumulada=Decimal("500.000"),
    consumo_periodo=Decimal("10.000"),
    es_anomalo=False,
)


def fila(
    numero_linea: int = 2,
    torre: str = "T01",
    apartamento: str = "101",
    servicio: str = "AGUA",
    periodo: str = "2026-03",
    lectura_acumulada: str = "510.5",
    fecha_lectura: str = "2026-04-02",
    celdas_sobrantes: tuple[str, ...] = (),
) -> FilaCruda:
    return FilaCruda(numero_linea, torre, apartamento, servicio, periodo, lectura_acumulada, fecha_lectura, celdas_sobrantes)


def validar(*filas_crudas: FilaCruda) -> tuple[list[LecturaValidada], list[FilaRechazada]]:
    validador = ValidadorFilas(TORRE, PERIODO_ARCHIVO, (APARTAMENTO_101, APARTAMENTO_102), (AGUA,), (LECTURA_ANTERIOR_101,))
    resultado = validador.validar_filas(filas_crudas)
    return list(resultado.lecturas_validadas), list(resultado.filas_rechazadas)


def prueba_fila_valida() -> None:
    lecturas_validadas, filas_rechazadas = validar(fila())
    assert filas_rechazadas == []
    assert lecturas_validadas[0].lectura_acumulada == Decimal("510.5")
    assert lecturas_validadas[0].fecha_lectura == date(2026, 4, 2)
    assert lecturas_validadas[0].apartamento == APARTAMENTO_101


def prueba_lectura_igual_a_la_anterior_es_valida() -> None:
    lecturas_validadas, _ = validar(fila(lectura_acumulada="500"))
    assert len(lecturas_validadas) == 1


@pytest.mark.parametrize(
    ("fila_cruda", "motivo_esperado", "valor_recibido_esperado"),
    [
        (fila(celdas_sobrantes=("x",)), MotivoRechazo.COLUMNAS_SOBRANTES, "x"),
        (fila(lectura_acumulada=""), MotivoRechazo.CAMPO_OBLIGATORIO_FALTANTE, None),
        (fila(fecha_lectura=""), MotivoRechazo.CAMPO_OBLIGATORIO_FALTANTE, None),
        (fila(torre="T02"), MotivoRechazo.TORRE_DISTINTA_A_LA_DEL_ARCHIVO, "T02"),
        (fila(periodo="2026-02"), MotivoRechazo.PERIODO_DISTINTO_AL_DEL_ARCHIVO, "2026-02"),
        (fila(lectura_acumulada="N/D"), MotivoRechazo.LECTURA_NO_NUMERICA, "N/D"),
        (fila(lectura_acumulada="12,5,8"), MotivoRechazo.LECTURA_NO_NUMERICA, "12,5,8"),
        (fila(lectura_acumulada="1e3"), MotivoRechazo.LECTURA_NO_NUMERICA, "1e3"),
        (fila(lectura_acumulada="-1"), MotivoRechazo.LECTURA_FUERA_DE_RANGO, "-1"),
        (fila(lectura_acumulada="510.1234"), MotivoRechazo.LECTURA_FUERA_DE_RANGO, "510.1234"),
        (fila(fecha_lectura="2026-02-30"), MotivoRechazo.FECHA_LECTURA_INVALIDA, "2026-02-30"),
        (fila(fecha_lectura="02/04/2026"), MotivoRechazo.FECHA_LECTURA_INVALIDA, "02/04/2026"),
        (fila(apartamento="999"), MotivoRechazo.APARTAMENTO_INEXISTENTE, "999"),
        (fila(servicio="GAS"), MotivoRechazo.SERVICIO_INEXISTENTE, "GAS"),
        (fila(lectura_acumulada="499.9"), MotivoRechazo.LECTURA_MENOR_QUE_LA_ANTERIOR, "499.9"),
    ],
)
def prueba_motivos_de_rechazo(fila_cruda: FilaCruda, motivo_esperado: MotivoRechazo, valor_recibido_esperado: str | None) -> None:
    lecturas_validadas, filas_rechazadas = validar(fila_cruda)
    assert lecturas_validadas == []
    assert filas_rechazadas[0].motivo_rechazo == motivo_esperado
    assert filas_rechazadas[0].valor_recibido == valor_recibido_esperado


def prueba_tripleta_repetida_rechaza_todas_sus_apariciones() -> None:
    lecturas_validadas, filas_rechazadas = validar(fila(numero_linea=2), fila(numero_linea=3), fila(numero_linea=4, apartamento="102"))
    assert [lectura.apartamento.numero for lectura in lecturas_validadas] == ["102"]
    assert [rechazo.fila_cruda.numero_linea for rechazo in filas_rechazadas] == [2, 3]
    assert {rechazo.motivo_rechazo for rechazo in filas_rechazadas} == {MotivoRechazo.TRIPLETA_REPETIDA_EN_ARCHIVO}


def prueba_carga_parcial_separa_aceptadas_y_rechazadas() -> None:
    lecturas_validadas, filas_rechazadas = validar(fila(), fila(numero_linea=3, apartamento="102", lectura_acumulada="N/D"))
    assert len(lecturas_validadas) == 1
    assert len(filas_rechazadas) == 1
