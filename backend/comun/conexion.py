import psycopg2
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor

from comun.configuracion import ConfiguracionBaseDatos
from comun.excepciones import ErrorConexionBaseDatos


Conexion = connection
Cursor = RealDictCursor


def abrir_conexion(configuracion: ConfiguracionBaseDatos) -> Conexion:
    try:
        conexion = psycopg2.connect(
            host=configuracion.host,
            port=configuracion.puerto,
            user=configuracion.usuario,
            password=configuracion.clave,
            dbname=configuracion.nombre_base_datos,
            client_encoding="UTF8",
            cursor_factory=RealDictCursor,
        )
    except psycopg2.Error as error:
        raise ErrorConexionBaseDatos(str(error)) from error
    conexion.autocommit = False
    return conexion
