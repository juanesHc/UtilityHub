from collections.abc import Callable

from pymysql.connections import Connection
from pymysql.cursors import Cursor


def ejecutar_en_transaccion[Resultado](
    abrir_conexion: Callable[[], Connection],
    operacion: Callable[[Cursor], Resultado],
) -> Resultado:
    conexion = abrir_conexion()
    try:
        conexion.begin()
        with conexion.cursor() as cursor:
            resultado = operacion(cursor)
        conexion.commit()
        return resultado
    except BaseException:
        conexion.rollback()
        raise
    finally:
        conexion.close()
