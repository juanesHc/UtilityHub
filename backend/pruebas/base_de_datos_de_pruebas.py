import os
from functools import partial
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extensions import connection

from comun.conexion import abrir_conexion
from comun.configuracion import cargar_configuracion_desde_entorno
from comun.modelos import ResultadoProcesamiento
from procesamiento.servicio import ServicioProcesamientoLecturas


DIRECTORIO_BACKEND: Path = Path(__file__).resolve().parent.parent
RUTA_ESQUEMA: Path = DIRECTORIO_BACKEND / "esquema.sql"
RUTA_GENERADOR: Path = DIRECTORIO_BACKEND.parent / "tools" / "generador-datos" / "generateTestCsv.py"
NOMBRE_BASE_DE_PRUEBAS: str = "utilityhub_pruebas"
CONFIGURACION_LOCAL_POR_DEFECTO: dict[str, str] = {
    "UTILITYHUB_DB_HOST": "localhost",
    "UTILITYHUB_DB_USUARIO": "utilityhub",
    "UTILITYHUB_DB_CLAVE": "localdev",
    "UTILITYHUB_DB_NOMBRE": "utilityhub",
    "UTILITYHUB_JWT_CLAVE_FIRMA": "clave-de-firma-exclusiva-de-las-pruebas-0123456789",
    "UTILITYHUB_CORS_ORIGENES": "http://localhost:5173",
}

for nombre_variable, valor_por_defecto in CONFIGURACION_LOCAL_POR_DEFECTO.items():
    os.environ.setdefault(nombre_variable, valor_por_defecto)
NOMBRE_BASE_DE_ADMINISTRACION: str = os.environ["UTILITYHUB_DB_NOMBRE"]
os.environ["UTILITYHUB_DB_NOMBRE"] = NOMBRE_BASE_DE_PRUEBAS


def conectar(nombre_base_datos: str) -> connection:
    return psycopg2.connect(
        host=os.environ["UTILITYHUB_DB_HOST"],
        port=int(os.environ.get("UTILITYHUB_DB_PUERTO") or 5432),
        user=os.environ["UTILITYHUB_DB_USUARIO"],
        password=os.environ["UTILITYHUB_DB_CLAVE"],
        dbname=nombre_base_datos,
        connect_timeout=3,
    )


def consultar(sentencia_sql: str, parametros: tuple[Any, ...] | None = None) -> list[tuple[Any, ...]]:
    conexion = conectar(NOMBRE_BASE_DE_PRUEBAS)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sentencia_sql, parametros)
            return cursor.fetchall()
    finally:
        conexion.close()


def ejecutar_y_confirmar(sentencia_sql: str, parametros: tuple[Any, ...] | None = None) -> int:
    conexion = conectar(NOMBRE_BASE_DE_PRUEBAS)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sentencia_sql, parametros)
            filas_afectadas = cursor.rowcount
        conexion.commit()
        return filas_afectadas
    finally:
        conexion.close()


def reiniciar_esquema() -> None:
    conexion = conectar(NOMBRE_BASE_DE_PRUEBAS)
    conexion.autocommit = True
    try:
        with conexion.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE")
            cursor.execute("CREATE SCHEMA public")
            cursor.execute(RUTA_ESQUEMA.read_text(encoding="utf-8"))
    finally:
        conexion.close()


def crear_servicio_procesamiento() -> ServicioProcesamientoLecturas:
    return ServicioProcesamientoLecturas(partial(abrir_conexion, cargar_configuracion_desde_entorno()))


def procesar_archivos_en_orden(directorio_lecturas: Path) -> list[ResultadoProcesamiento]:
    servicio_procesamiento = crear_servicio_procesamiento()
    return [
        servicio_procesamiento.procesar_archivo(ruta_archivo.name, ruta_archivo.read_bytes())
        for ruta_archivo in sorted(directorio_lecturas.glob("lecturas_*.csv"))
    ]
