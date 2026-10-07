import pytest

from comun.excepciones import ArchivoVacio, CodificacionNoSoportada, EncabezadoInvalido, NombreArchivoInvalido
from comun.modelos import Periodo
from procesamiento.normalizacion import interpretar_nombre_archivo, normalizar_contenido_csv


ENCABEZADO: str = "torre,apartamento,servicio,periodo,lectura_acumulada,fecha_lectura\r\n"


def prueba_nombre_de_archivo_valido() -> None:
    identificacion = interpretar_nombre_archivo("lecturas_T01_2026-03.csv")
    assert identificacion.codigo_torre == "T01"
    assert identificacion.periodo == Periodo(2026, 3)


def prueba_nombre_de_archivo_con_ruta_y_minusculas() -> None:
    identificacion = interpretar_nombre_archivo("entrada/2026/LECTURAS_t02_2026-12.CSV")
    assert identificacion.codigo_torre == "T02"
    assert identificacion.periodo == Periodo(2026, 12)


@pytest.mark.parametrize(
    "nombre_archivo",
    ["lecturas_T01_2026-13.csv", "lecturas_T01_2026-3.csv", "lecturas_01_2026-03.csv", "otro.csv", "carpeta\x00/lecturas_T01_2026-03.csv"],
)
def prueba_nombre_de_archivo_invalido(nombre_archivo: str) -> None:
    with pytest.raises(NombreArchivoInvalido):
        interpretar_nombre_archivo(nombre_archivo)


def prueba_normaliza_la_forma_sin_tocar_el_contenido() -> None:
    contenido = (ENCABEZADO + ' t01 , 101 , agua ,2026-03,"516,5",2026-04-02\r\n,,,,,\r\n\r\n').encode("utf-8-sig")
    filas_crudas = normalizar_contenido_csv(contenido)
    assert len(filas_crudas) == 1
    fila_cruda = filas_crudas[0]
    assert (fila_cruda.torre, fila_cruda.apartamento, fila_cruda.servicio) == ("T01", "101", "AGUA")
    assert fila_cruda.lectura_acumulada == "516.5"
    assert fila_cruda.numero_linea == 2


def prueba_no_rellena_valores_faltantes() -> None:
    filas_crudas = normalizar_contenido_csv((ENCABEZADO + "T01,101,AGUA,2026-03,\r\n").encode("utf-8"))
    assert filas_crudas[0].lectura_acumulada == ""
    assert filas_crudas[0].fecha_lectura == ""


def prueba_coma_decimal_ambigua_no_se_convierte() -> None:
    filas_crudas = normalizar_contenido_csv((ENCABEZADO + 'T01,101,AGUA,2026-03,"12,5,8",2026-04-02\r\n').encode("utf-8"))
    assert filas_crudas[0].lectura_acumulada == "12,5,8"


def prueba_celdas_sobrantes_se_conservan() -> None:
    filas_crudas = normalizar_contenido_csv((ENCABEZADO + "T01,101,AGUA,2026-03,516,0,2026-04-02\r\n").encode("utf-8"))
    assert filas_crudas[0].celdas_sobrantes == ("2026-04-02",)


def prueba_encabezado_en_otro_orden_es_valido() -> None:
    contenido = "apartamento,torre,servicio,periodo,fecha_lectura,lectura_acumulada\r\n101,T01,AGUA,2026-03,2026-04-02,5\r\n"
    assert normalizar_contenido_csv(contenido.encode("utf-8"))[0].lectura_acumulada == "5"


def prueba_encabezado_incorrecto() -> None:
    with pytest.raises(EncabezadoInvalido):
        normalizar_contenido_csv(b"torre,apartamento,servicio,periodo,consumo,fecha_lectura\r\n")


def prueba_archivo_vacio() -> None:
    with pytest.raises(ArchivoVacio):
        normalizar_contenido_csv(b"\r\n\r\n")


def prueba_codificacion_no_utf8() -> None:
    with pytest.raises(CodificacionNoSoportada):
        normalizar_contenido_csv((ENCABEZADO + "T01,101,ENERGÍA,2026-03,1,2026-04-02\r\n").encode("latin-1"))
