import hashlib
from pathlib import Path

import pytest

from comun.excepciones import NombreArchivoInvalido, PeriodoAnteriorAlMasReciente
from comun.modelos import EstadoCarga, MotivoRechazo
from pruebas.base_de_datos_de_pruebas import consultar, crear_servicio_procesamiento


ARCHIVO_ULTIMO_PERIODO_T01: str = "lecturas_T01_2026-09.csv"
ARCHIVO_PERIODO_ANTIGUO_T01: str = "lecturas_T01_2026-03.csv"


def huella_de_la_base() -> str:
    return " | ".join(
        f"{tabla}:{hashlib.sha256(repr(consultar(f'SELECT * FROM {tabla} ORDER BY 1')).encode()).hexdigest()}"
        for tabla in ("carga", "lectura", "rechazo")
    )


def prueba_reprocesar_el_ultimo_periodo_reemplaza_la_carga(base_con_lecturas_procesadas_exclusiva: Path) -> None:
    ruta_archivo = base_con_lecturas_procesadas_exclusiva / ARCHIVO_ULTIMO_PERIODO_T01
    id_carga_anterior = consultar(
        "SELECT id_carga FROM carga WHERE nombre_archivo = %s AND estado <> 'reemplazada'", (ARCHIVO_ULTIMO_PERIODO_T01,)
    )[0][0]
    rechazos_anteriores = consultar("SELECT COUNT(*) FROM rechazo WHERE id_carga = %s", (id_carga_anterior,))[0][0]
    total_lecturas_antes = consultar("SELECT COUNT(*) FROM lectura")[0][0]

    resultado = crear_servicio_procesamiento().procesar_archivo(ruta_archivo.name, ruta_archivo.read_bytes())

    assert resultado.ids_cargas_reemplazadas == (id_carga_anterior,)
    assert consultar("SELECT estado FROM carga WHERE id_carga = %s", (id_carga_anterior,))[0][0] == EstadoCarga.REEMPLAZADA.value
    assert consultar("SELECT COUNT(*) FROM lectura WHERE id_carga = %s", (id_carga_anterior,))[0][0] == 0
    assert consultar("SELECT COUNT(*) FROM rechazo WHERE id_carga = %s", (id_carga_anterior,))[0][0] == rechazos_anteriores
    assert consultar("SELECT COUNT(*) FROM lectura")[0][0] == total_lecturas_antes
    assert consultar(
        "SELECT COUNT(*) FROM carga WHERE nombre_archivo = %s AND estado <> 'reemplazada'", (ARCHIVO_ULTIMO_PERIODO_T01,)
    )[0][0] == 1


def prueba_reprocesar_un_periodo_antiguo_no_deja_rastro(base_con_lecturas_procesadas_exclusiva: Path) -> None:
    ruta_archivo = base_con_lecturas_procesadas_exclusiva / ARCHIVO_PERIODO_ANTIGUO_T01
    huella_antes = huella_de_la_base()
    with pytest.raises(PeriodoAnteriorAlMasReciente):
        crear_servicio_procesamiento().procesar_archivo(ruta_archivo.name, ruta_archivo.read_bytes())
    assert huella_de_la_base() == huella_antes
    assert consultar(
        "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database() AND state LIKE 'idle in transaction%%'"
    )[0][0] == 0


def prueba_caracter_nul_se_rechaza_sin_deshacer_la_carga(base_vacia: None) -> None:
    nul = chr(0)
    contenido = (
        "torre,apartamento,servicio,periodo,lectura_acumulada,fecha_lectura\r\n"
        "T01,101,AGUA,2025-10,500,2025-11-02\r\n"
        f"T01,10{nul}2,AGUA,2025-10,500,2025-11-02\r\n"
        f"T01,103,AGUA,2025-10,5{nul}00,2025-11-02\r\n"
    ).encode("utf-8")
    resultado = crear_servicio_procesamiento().procesar_archivo("lecturas_T01_2025-10.csv", contenido)
    assert resultado.estado_carga == EstadoCarga.PROCESADA_PARCIAL
    assert consultar("SELECT apartamento, motivo, valor_recibido FROM rechazo ORDER BY numero_fila") == [
        ("10�2", MotivoRechazo.APARTAMENTO_INEXISTENTE.value, "10�2"),
        ("103", MotivoRechazo.LECTURA_NO_NUMERICA.value, "5�00"),
    ]
    assert consultar("SELECT COUNT(*) FROM lectura")[0][0] == 1


def prueba_nombre_de_archivo_con_nul_se_rechaza_antes_de_tocar_la_base(base_vacia: None) -> None:
    with pytest.raises(NombreArchivoInvalido):
        crear_servicio_procesamiento().procesar_archivo("entrada\x00/lecturas_T01_2025-10.csv", b"")
    assert consultar("SELECT COUNT(*) FROM carga")[0][0] == 0
