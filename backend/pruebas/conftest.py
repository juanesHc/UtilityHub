import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import psycopg2
import pytest

from pruebas.base_de_datos_de_pruebas import (
    NOMBRE_BASE_DE_ADMINISTRACION,
    NOMBRE_BASE_DE_PRUEBAS,
    RUTA_GENERADOR,
    conectar,
    procesar_archivos_en_orden,
    reiniciar_esquema,
)


@pytest.fixture(scope="session")
def base_de_pruebas() -> Iterator[None]:
    try:
        conexion_administracion = conectar(NOMBRE_BASE_DE_ADMINISTRACION)
    except psycopg2.OperationalError as error:
        pytest.skip(f"PostgreSQL no disponible; levantelo con 'docker compose up -d'. Detalle: {error}")
    conexion_administracion.autocommit = True
    with conexion_administracion.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS {NOMBRE_BASE_DE_PRUEBAS} WITH (FORCE)")
        cursor.execute(f"CREATE DATABASE {NOMBRE_BASE_DE_PRUEBAS}")
    try:
        yield
    finally:
        with conexion_administracion.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS {NOMBRE_BASE_DE_PRUEBAS} WITH (FORCE)")
        conexion_administracion.close()


@pytest.fixture(scope="session")
def directorio_lecturas_generadas(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directorio_lecturas = tmp_path_factory.mktemp("lecturas_generadas")
    subprocess.run(
        [sys.executable, str(RUTA_GENERADOR), "--salida", str(directorio_lecturas)],
        check=True,
        capture_output=True,
    )
    return directorio_lecturas


@pytest.fixture
def base_vacia(base_de_pruebas: None) -> None:
    reiniciar_esquema()


@pytest.fixture(scope="module")
def base_con_lecturas_procesadas(base_de_pruebas: None, directorio_lecturas_generadas: Path) -> Path:
    reiniciar_esquema()
    procesar_archivos_en_orden(directorio_lecturas_generadas)
    return directorio_lecturas_generadas


@pytest.fixture
def base_con_lecturas_procesadas_exclusiva(base_de_pruebas: None, directorio_lecturas_generadas: Path) -> Path:
    reiniciar_esquema()
    procesar_archivos_en_orden(directorio_lecturas_generadas)
    return directorio_lecturas_generadas
