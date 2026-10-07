import os
from collections.abc import Iterator
from datetime import datetime, timedelta
from functools import partial

import pytest
from fastapi.testclient import TestClient

from api.main import crear_aplicacion
from api.servicio_autenticacion import DURACION_BLOQUEO, MAXIMO_INTENTOS_FALLIDOS, ServicioAutenticacion
from api.servicio_usuarios import ServicioUsuarios
from comun.conexion import abrir_conexion
from comun.configuracion import cargar_configuracion_desde_entorno
from comun.excepciones import CredencialesInvalidas, CuentaBloqueada
from comun.reloj import obtener_fecha_hora_actual_utc
from pruebas.base_de_datos_de_pruebas import consultar, ejecutar_y_confirmar


CLAVE_SEMBRADA: str = "UtilityHub-zXNWjx2EntCE"
CLAVE_NUEVA: str = "una-clave-nueva-bastante-larga"


class RelojManual:
    def __init__(self, fecha_inicial: datetime) -> None:
        self.fecha_actual: datetime = fecha_inicial

    def __call__(self) -> datetime:
        return self.fecha_actual

    def avanzar(self, intervalo: timedelta) -> None:
        self.fecha_actual = self.fecha_actual + intervalo


@pytest.fixture
def cliente(base_vacia: None) -> Iterator[TestClient]:
    with TestClient(crear_aplicacion()) as cliente_http:
        yield cliente_http


def iniciar_sesion(cliente: TestClient, usuario: str, clave: str) -> tuple[int, dict[str, object], dict[str, str]]:
    respuesta = cliente.post("/api/auth/login", json={"usuario": usuario, "clave": clave})
    return respuesta.status_code, respuesta.json(), dict(respuesta.headers)


def encabezados_de(cliente: TestClient, usuario: str, clave: str) -> dict[str, str]:
    estado, cuerpo, _ = iniciar_sesion(cliente, usuario, clave)
    assert estado == 200, cuerpo
    return {"Authorization": f"Bearer {cuerpo['token_acceso']}"}


def crear_servicio_autenticacion(reloj: RelojManual) -> ServicioAutenticacion:
    return ServicioAutenticacion(
        partial(abrir_conexion, cargar_configuracion_desde_entorno()),
        os.environ["UTILITYHUB_JWT_CLAVE_FIRMA"],
        reloj,
    )


def crear_servicio_usuarios() -> ServicioUsuarios:
    return ServicioUsuarios(partial(abrir_conexion, cargar_configuracion_desde_entorno()))


def prueba_cuatro_fallos_no_bloquean_y_el_acierto_reinicia_el_contador(cliente: TestClient) -> None:
    for _ in range(MAXIMO_INTENTOS_FALLIDOS - 1):
        assert iniciar_sesion(cliente, "admin", "clave-incorrecta")[0] == 401
    assert consultar("SELECT intentos_fallidos FROM usuario WHERE nombre_usuario = 'admin'") == [(MAXIMO_INTENTOS_FALLIDOS - 1,)]
    assert iniciar_sesion(cliente, "admin", CLAVE_SEMBRADA)[0] == 200
    assert consultar("SELECT intentos_fallidos, bloqueado_hasta FROM usuario WHERE nombre_usuario = 'admin'") == [(0, None)]


def prueba_el_quinto_fallo_bloquea_incluso_con_la_clave_correcta(cliente: TestClient) -> None:
    for _ in range(MAXIMO_INTENTOS_FALLIDOS - 1):
        assert iniciar_sesion(cliente, "admin", "clave-incorrecta")[0] == 401
    estado, cuerpo, encabezados = iniciar_sesion(cliente, "admin", "clave-incorrecta")
    assert estado == 429
    assert "bloqueada" in str(cuerpo["detail"])
    assert 0 < int(encabezados["retry-after"]) <= DURACION_BLOQUEO.total_seconds()

    estado, _, encabezados = iniciar_sesion(cliente, "ADMIN", CLAVE_SEMBRADA)
    assert estado == 429
    assert "retry-after" in encabezados


def prueba_el_bloqueo_vence_y_el_contador_reinicia(base_vacia: None) -> None:
    reloj = RelojManual(obtener_fecha_hora_actual_utc())
    servicio_autenticacion = crear_servicio_autenticacion(reloj)
    for _ in range(MAXIMO_INTENTOS_FALLIDOS - 1):
        with pytest.raises(CredencialesInvalidas):
            servicio_autenticacion.iniciar_sesion("admin", "clave-incorrecta")
    with pytest.raises(CuentaBloqueada):
        servicio_autenticacion.iniciar_sesion("admin", "clave-incorrecta")

    reloj.avanzar(DURACION_BLOQUEO - timedelta(seconds=1))
    with pytest.raises(CuentaBloqueada) as bloqueo:
        servicio_autenticacion.iniciar_sesion("admin", CLAVE_SEMBRADA)
    assert bloqueo.value.segundos_restantes == 1

    reloj.avanzar(timedelta(seconds=1))
    with pytest.raises(CredencialesInvalidas):
        servicio_autenticacion.iniciar_sesion("admin", "clave-incorrecta")
    assert consultar("SELECT intentos_fallidos, bloqueado_hasta FROM usuario WHERE nombre_usuario = 'admin'") == [(1, None)]
    assert servicio_autenticacion.iniciar_sesion("admin", CLAVE_SEMBRADA).token_acceso


def prueba_usuario_inexistente_nunca_se_bloquea(cliente: TestClient) -> None:
    respuestas = [iniciar_sesion(cliente, "fantasma", "clave-incorrecta")[0] for _ in range(MAXIMO_INTENTOS_FALLIDOS + 1)]
    assert respuestas == [401] * (MAXIMO_INTENTOS_FALLIDOS + 1)


def prueba_cambiar_la_clave_desbloquea_la_cuenta(cliente: TestClient) -> None:
    for _ in range(MAXIMO_INTENTOS_FALLIDOS):
        iniciar_sesion(cliente, "admin", "clave-incorrecta")
    assert iniciar_sesion(cliente, "admin", CLAVE_SEMBRADA)[0] == 429
    crear_servicio_usuarios().cambiar_clave("admin", CLAVE_NUEVA)
    assert iniciar_sesion(cliente, "admin", CLAVE_NUEVA)[0] == 200


def prueba_cambiar_la_clave_invalida_los_tokens_anteriores(cliente: TestClient) -> None:
    encabezados_anteriores = encabezados_de(cliente, "admin", CLAVE_SEMBRADA)
    assert cliente.get("/api/torres", headers=encabezados_anteriores).status_code == 200

    crear_servicio_usuarios().cambiar_clave("admin", CLAVE_NUEVA)

    assert cliente.get("/api/torres", headers=encabezados_anteriores).status_code == 401
    encabezados_nuevos = encabezados_de(cliente, "admin", CLAVE_NUEVA)
    assert cliente.get("/api/torres", headers=encabezados_nuevos).status_code == 200


def prueba_token_de_usuario_eliminado_deja_de_valer(cliente: TestClient) -> None:
    crear_servicio_usuarios().registrar_usuario("temporal", CLAVE_NUEVA)
    encabezados_temporal = encabezados_de(cliente, "temporal", CLAVE_NUEVA)
    assert cliente.get("/api/torres", headers=encabezados_temporal).status_code == 200
    assert ejecutar_y_confirmar("DELETE FROM usuario WHERE nombre_usuario = 'temporal'") == 1
    assert cliente.get("/api/torres", headers=encabezados_temporal).status_code == 401


def prueba_un_admin_registra_a_otro_y_este_puede_registrar_a_un_tercero(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/api/usuarios",
        json={"usuario": "supervisora", "clave": CLAVE_NUEVA},
        headers=encabezados_de(cliente, "admin", CLAVE_SEMBRADA),
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["nombre_usuario"] == "supervisora"
    assert respuesta.json()["creado_por"] == "admin"

    respuesta = cliente.post(
        "/api/usuarios",
        json={"usuario": "operador", "clave": CLAVE_NUEVA},
        headers=encabezados_de(cliente, "supervisora", CLAVE_NUEVA),
    )
    assert respuesta.status_code == 201
    assert consultar(
        "SELECT u.nombre_usuario, c.nombre_usuario, u.fecha_creacion IS NOT NULL FROM usuario u "
        "LEFT JOIN usuario c ON c.id_usuario = u.creado_por_id_usuario ORDER BY u.id_usuario"
    ) == [("admin", None, False), ("supervisora", "admin", True), ("operador", "supervisora", True)]


def prueba_registro_sin_token_devuelve_401(cliente: TestClient) -> None:
    respuesta = cliente.post("/api/usuarios", json={"usuario": "intruso", "clave": CLAVE_NUEVA})
    assert respuesta.status_code == 401
    assert consultar("SELECT COUNT(*) FROM usuario") == [(1,)]


@pytest.mark.parametrize(
    ("usuario", "clave", "codigo_esperado"),
    [
        ("ADMIN", CLAVE_NUEVA, 409),
        ("nuevo", "corta", 422),
        (" nuevo", CLAVE_NUEVA, 422),
        ("nu\x00evo", CLAVE_NUEVA, 422),
        ("nuevo", CLAVE_NUEVA + "\x00", 422),
        ("x" * 51, CLAVE_NUEVA, 422),
    ],
)
def prueba_registro_rechazado(cliente: TestClient, usuario: str, clave: str, codigo_esperado: int) -> None:
    respuesta = cliente.post(
        "/api/usuarios",
        json={"usuario": usuario, "clave": clave},
        headers=encabezados_de(cliente, "admin", CLAVE_SEMBRADA),
    )
    assert respuesta.status_code == codigo_esperado, respuesta.text
    assert consultar("SELECT COUNT(*) FROM usuario") == [(1,)]


def prueba_bloqueo_legible_desde_otro_origen(cliente: TestClient) -> None:
    origen = "http://localhost:5173"
    for _ in range(MAXIMO_INTENTOS_FALLIDOS - 1):
        cliente.post("/api/auth/login", json={"usuario": "admin", "clave": "clave-incorrecta"}, headers={"Origin": origen})
    respuesta = cliente.post(
        "/api/auth/login",
        json={"usuario": "admin", "clave": "clave-incorrecta"},
        headers={"Origin": origen},
    )
    assert respuesta.status_code == 429
    assert respuesta.headers["access-control-allow-origin"] == origen
    assert "retry-after" in respuesta.headers["access-control-expose-headers"].lower()
    assert int(respuesta.headers["retry-after"]) > 0


def prueba_registro_devuelve_fecha_utc(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/api/usuarios",
        json={"usuario": "nueva", "clave": CLAVE_NUEVA},
        headers=encabezados_de(cliente, "admin", CLAVE_SEMBRADA),
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["fecha_creacion"].endswith("Z")


def prueba_listado_de_administradores(cliente: TestClient) -> None:
    encabezados = encabezados_de(cliente, "admin", CLAVE_SEMBRADA)
    for nombre in ("zeta.porteria", "Beta.Contabilidad"):
        assert cliente.post("/api/usuarios", json={"usuario": nombre, "clave": CLAVE_NUEVA}, headers=encabezados).status_code == 201
    respuesta = cliente.get("/api/usuarios", headers=encabezados)
    assert respuesta.status_code == 200
    administradores = respuesta.json()
    assert [a["nombre_usuario"] for a in administradores] == ["admin", "Beta.Contabilidad", "zeta.porteria"]
    assert [a["creado_por"] for a in administradores] == [None, "admin", "admin"]
    assert administradores[0]["ultimo_acceso"].endswith("Z")
    assert administradores[1]["ultimo_acceso"] is None
    assert administradores[1]["fecha_creacion"].endswith("Z")
    assert all(set(a) == {"id_usuario", "nombre_usuario", "fecha_creacion", "creado_por", "ultimo_acceso", "esta_bloqueado"} for a in administradores)
    assert "hash" not in respuesta.text and CLAVE_NUEVA not in respuesta.text


def prueba_listado_marca_cuentas_bloqueadas(cliente: TestClient) -> None:
    encabezados = encabezados_de(cliente, "admin", CLAVE_SEMBRADA)
    cliente.post("/api/usuarios", json={"usuario": "intrusa.probable", "clave": CLAVE_NUEVA}, headers=encabezados)
    for _ in range(MAXIMO_INTENTOS_FALLIDOS):
        iniciar_sesion(cliente, "intrusa.probable", "clave-incorrecta")
    bloqueo = {a["nombre_usuario"]: a["esta_bloqueado"] for a in cliente.get("/api/usuarios", headers=encabezados).json()}
    assert bloqueo == {"admin": False, "intrusa.probable": True}


def prueba_listado_sin_token_devuelve_401(cliente: TestClient) -> None:
    assert cliente.get("/api/usuarios").status_code == 401
