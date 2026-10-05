import pymysql
from pymysql.connections import Connection

from comun.configuracion import ConfiguracionBaseDatos
from comun.excepciones import ErrorConexionBaseDatos


def abrir_conexion(configuracion: ConfiguracionBaseDatos) -> Connection:
    try:
        return pymysql.connect(
            host=configuracion.host,
            port=configuracion.puerto,
            user=configuracion.usuario,
            password=configuracion.clave,
            database=configuracion.nombre_base_datos,
            charset="utf8mb4",
            autocommit=False,
        )
    except pymysql.MySQLError as error:
        raise ErrorConexionBaseDatos(str(error)) from error
