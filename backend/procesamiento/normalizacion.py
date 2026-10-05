import csv
import io
import re
from collections.abc import Iterator

from comun.excepciones import (
    ArchivoVacio,
    CodificacionNoSoportada,
    EncabezadoInvalido,
    NombreArchivoInvalido,
    PeriodoInvalido,
)
from comun.modelos import FilaCruda, IdentificacionArchivo, Periodo


COLUMNAS_ESPERADAS: tuple[str, ...] = (
    "torre",
    "apartamento",
    "servicio",
    "periodo",
    "lectura_acumulada",
    "fecha_lectura",
)
PATRON_NOMBRE_ARCHIVO: re.Pattern[str] = re.compile(
    r"lecturas_(t[0-9]+)_([0-9]{4}-[0-9]{2})\.csv",
    re.IGNORECASE,
)
PATRON_SEPARADOR_DE_RUTA: re.Pattern[str] = re.compile(r"[\\/]")


def interpretar_nombre_archivo(nombre_archivo: str) -> IdentificacionArchivo:
    nombre_sin_ruta = PATRON_SEPARADOR_DE_RUTA.split(nombre_archivo.strip())[-1]
    coincidencia = PATRON_NOMBRE_ARCHIVO.fullmatch(nombre_sin_ruta)
    if coincidencia is None:
        raise NombreArchivoInvalido(nombre_archivo)
    try:
        periodo = Periodo.desde_texto(coincidencia.group(2))
    except PeriodoInvalido as error:
        raise NombreArchivoInvalido(nombre_archivo) from error
    return IdentificacionArchivo(codigo_torre=coincidencia.group(1).upper(), periodo=periodo)


def normalizar_contenido_csv(contenido_archivo: bytes) -> tuple[FilaCruda, ...]:
    lector_csv = csv.reader(io.StringIO(decodificar_contenido(contenido_archivo), newline=""))
    encabezado = leer_encabezado(lector_csv)
    filas_crudas: list[FilaCruda] = []
    for celdas in lector_csv:
        celdas_recortadas = [celda.strip() for celda in celdas]
        if not any(celdas_recortadas):
            continue
        filas_crudas.append(construir_fila_cruda(lector_csv.line_num, encabezado, celdas_recortadas))
    return tuple(filas_crudas)


def decodificar_contenido(contenido_archivo: bytes) -> str:
    try:
        return contenido_archivo.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CodificacionNoSoportada() from error


def leer_encabezado(lector_csv: Iterator[list[str]]) -> tuple[str, ...]:
    for celdas in lector_csv:
        nombres_columnas = tuple(celda.strip().lower() for celda in celdas)
        if not any(nombres_columnas):
            continue
        if sorted(nombres_columnas) != sorted(COLUMNAS_ESPERADAS):
            raise EncabezadoInvalido(nombres_columnas, COLUMNAS_ESPERADAS)
        return nombres_columnas
    raise ArchivoVacio()


def construir_fila_cruda(numero_linea: int, encabezado: tuple[str, ...], celdas: list[str]) -> FilaCruda:
    valor_por_columna = dict(zip(encabezado, celdas))
    return FilaCruda(
        numero_linea=numero_linea,
        torre=valor_por_columna.get("torre", "").upper(),
        apartamento=valor_por_columna.get("apartamento", ""),
        servicio=valor_por_columna.get("servicio", "").upper(),
        periodo=valor_por_columna.get("periodo", ""),
        lectura_acumulada=unificar_separador_decimal(valor_por_columna.get("lectura_acumulada", "")),
        fecha_lectura=valor_por_columna.get("fecha_lectura", ""),
        celdas_sobrantes=tuple(celda for celda in celdas[len(encabezado):] if celda),
    )


def unificar_separador_decimal(texto_lectura: str) -> str:
    if texto_lectura.count(",") == 1 and "." not in texto_lectura:
        return texto_lectura.replace(",", ".")
    return texto_lectura
