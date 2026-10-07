import os
import subprocess
import sys
from functools import partial

import pytest

from api.servicio_autenticacion import ServicioAutenticacion
from api.servicio_usuarios import ServicioUsuarios
from comun.conexion import abrir_conexion
from comun.configuracion import cargar_configuracion_desde_entorno
from comun.excepciones import (
    ClaveInsegura,
    CredencialesInvalidas,
    NombreUsuarioInvalido,
    UsuarioInexistente,
    UsuarioYaExiste,
)
from pruebas.base_de_datos_de_pruebas import DIRECTORIO_BACKEND, consultar


CLAVE_VALIDA: str = "una-clave-larga-y-valida"


def crear_servicio_usuarios() -> ServicioUsuarios:
    return ServicioUsuarios(partial(abrir_conexion, cargar_configuracion_desde_entorno()))


def iniciar_sesion(nombre_usuario: str, clave_en_claro: str) -> str:
    servicio_autenticacion = ServicioAutenticacion(
        partial(abrir_conexion, cargar_configuracion_desde_entorno()),
        os.environ["UTILITYHUB_JWT_CLAVE_FIRMA"],
    )
    token_emitido = servicio_autenticacion.iniciar_sesion(nombre_usuario, clave_en_claro)
    return servicio_autenticacion.verificar_token(token_emitido.token_acceso).nombre_usuario


def ejecutar_comando(accion: str, nombre_usuario: str, clave_en_claro: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "api.administrar_usuarios", accion, nombre_usuario, "--clave-por-entrada-estandar"],
        input=clave_en_claro + "\n",
        cwd=DIRECTORIO_BACKEND,
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )


def prueba_registrar_usuario_y_entrar(base_vacia: None) -> None:
    crear_servicio_usuarios().registrar_usuario("operador", CLAVE_VALIDA)
    assert iniciar_sesion("OPERADOR", CLAVE_VALIDA) == "operador"
    hash_guardado = consultar("SELECT hash_contrasena FROM usuario WHERE nombre_usuario = 'operador'")[0][0]
    assert CLAVE_VALIDA not in hash_guardado


def prueba_usuario_repetido_sin_distinguir_mayusculas(base_vacia: None) -> None:
    with pytest.raises(UsuarioYaExiste):
        crear_servicio_usuarios().registrar_usuario("ADMIN", CLAVE_VALIDA)


@pytest.mark.parametrize("nombre_usuario", ["", " operador", "operador ", "a" * 51, "oper\x00ador", "oper\tador"])
def prueba_nombre_de_usuario_invalido(base_vacia: None, nombre_usuario: str) -> None:
    with pytest.raises(NombreUsuarioInvalido):
        crear_servicio_usuarios().registrar_usuario(nombre_usuario, CLAVE_VALIDA)


@pytest.mark.parametrize("clave_en_claro", ["corta", "a" * 11, "a" * 129, "una-clave-larga\x00"])
def prueba_clave_inaceptable(base_vacia: None, clave_en_claro: str) -> None:
    with pytest.raises(ClaveInsegura):
        crear_servicio_usuarios().registrar_usuario("operador", clave_en_claro)
    assert consultar("SELECT COUNT(*) FROM usuario WHERE nombre_usuario = 'operador'")[0][0] == 0


def prueba_cambiar_clave_invalida_la_anterior(base_vacia: None) -> None:
    crear_servicio_usuarios().cambiar_clave("Admin", CLAVE_VALIDA)
    assert iniciar_sesion("admin", CLAVE_VALIDA) == "admin"
    with pytest.raises(CredencialesInvalidas):
        iniciar_sesion("admin", "UtilityHub-zXNWjx2EntCE")


def prueba_cambiar_clave_de_usuario_inexistente(base_vacia: None) -> None:
    with pytest.raises(UsuarioInexistente):
        crear_servicio_usuarios().cambiar_clave("fantasma", CLAVE_VALIDA)


def prueba_comando_crear_y_cambiar_clave(base_vacia: None) -> None:
    creacion = ejecutar_comando("crear", "supervisora", CLAVE_VALIDA)
    assert creacion.returncode == 0, creacion.stderr
    assert "creado" in creacion.stdout
    assert iniciar_sesion("supervisora", CLAVE_VALIDA) == "supervisora"

    cambio = ejecutar_comando("cambiar-clave", "supervisora", "otra-clave-larga-y-valida")
    assert cambio.returncode == 0, cambio.stderr
    assert iniciar_sesion("supervisora", "otra-clave-larga-y-valida") == "supervisora"


def prueba_comando_informa_errores_sin_traza(base_vacia: None) -> None:
    resultado = ejecutar_comando("crear", "admin", CLAVE_VALIDA)
    assert resultado.returncode == 1
    assert resultado.stderr.startswith("Error: Ya existe un usuario")
    assert "Traceback" not in resultado.stderr
