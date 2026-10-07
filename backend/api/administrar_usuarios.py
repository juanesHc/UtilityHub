import argparse
import getpass
import sys
from functools import partial

from api.servicio_usuarios import ServicioUsuarios
from comun.conexion import abrir_conexion
from comun.configuracion import cargar_configuracion_desde_entorno
from comun.excepciones import ErrorUtilityHub


ACCION_CREAR: str = "crear"
ACCION_CAMBIAR_CLAVE: str = "cambiar-clave"


class ClavesNoCoinciden(Exception):
    pass


def construir_analizador_argumentos() -> argparse.ArgumentParser:
    analizador = argparse.ArgumentParser(
        prog="python -m api.administrar_usuarios",
        description="Crea usuarios de UtilityHub o cambia su clave. La clave nunca se pasa como argumento.",
    )
    analizador.add_argument("accion", choices=(ACCION_CREAR, ACCION_CAMBIAR_CLAVE))
    analizador.add_argument("nombre_usuario")
    analizador.add_argument(
        "--clave-por-entrada-estandar",
        action="store_true",
        help="lee la clave de la primera línea de la entrada estándar, para uso desde scripts",
    )
    return analizador


def leer_clave(leer_de_entrada_estandar: bool) -> str:
    if leer_de_entrada_estandar:
        return sys.stdin.readline().rstrip("\r\n")
    clave_en_claro = getpass.getpass("Clave: ")
    if getpass.getpass("Repita la clave: ") != clave_en_claro:
        raise ClavesNoCoinciden()
    return clave_en_claro


def main() -> int:
    argumentos = construir_analizador_argumentos().parse_args()
    try:
        clave_en_claro = leer_clave(argumentos.clave_por_entrada_estandar)
    except ClavesNoCoinciden:
        print("Error: las claves no coinciden", file=sys.stderr)
        return 1

    try:
        servicio_usuarios = ServicioUsuarios(partial(abrir_conexion, cargar_configuracion_desde_entorno()))
        if argumentos.accion == ACCION_CREAR:
            usuario_registrado = servicio_usuarios.registrar_usuario(argumentos.nombre_usuario, clave_en_claro)
            print(f"Usuario '{usuario_registrado.nombre_usuario}' creado con id {usuario_registrado.id_usuario}")
        else:
            servicio_usuarios.cambiar_clave(argumentos.nombre_usuario, clave_en_claro)
            print(f"Clave de '{argumentos.nombre_usuario}' actualizada")
    except ErrorUtilityHub as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
