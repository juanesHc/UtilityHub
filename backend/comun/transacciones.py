from collections.abc import Callable

from comun.conexion import Conexion, Cursor


def ejecutar_en_transaccion[Resultado](
    abrir_conexion: Callable[[], Conexion],
    operacion: Callable[[Cursor], Resultado],
) -> Resultado:
    conexion = abrir_conexion()
    try:
        with conexion.cursor() as cursor:
            resultado = operacion(cursor)
        conexion.commit()
        return resultado
    except BaseException:
        conexion.rollback()
        raise
    finally:
        conexion.close()
