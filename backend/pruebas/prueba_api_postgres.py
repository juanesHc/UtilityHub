import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import crear_aplicacion
from api.servicio_autenticacion import DURACION_TOKEN, ServicioAutenticacion
from comun.conexion import Conexion
from comun.reloj import obtener_fecha_hora_actual_utc
from pruebas.base_de_datos_de_pruebas import consultar


USUARIO_SEMBRADO: str = "admin"
CLAVE_SEMBRADA: str = "UtilityHub-zXNWjx2EntCE"
ORIGEN_PERMITIDO: str = "http://localhost:5173"


def conexion_no_permitida() -> Conexion:
    raise AssertionError("no se esperaba acceso a la base de datos")


@pytest.fixture(scope="module")
def cliente(base_con_lecturas_procesadas: Path) -> Iterator[TestClient]:
    with TestClient(crear_aplicacion()) as cliente_http:
        yield cliente_http


@pytest.fixture(scope="module")
def encabezados_autenticados(cliente: TestClient) -> dict[str, str]:
    respuesta = cliente.post("/api/auth/login", json={"usuario": USUARIO_SEMBRADO, "clave": CLAVE_SEMBRADA})
    return {"Authorization": "Bearer " + respuesta.json()["token_acceso"]}


def obtener(cliente: TestClient, encabezados: dict[str, str], ruta: str) -> Any:
    respuesta = cliente.get(ruta, headers=encabezados)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def prueba_login_correcto_registra_el_acceso(cliente: TestClient) -> None:
    respuesta = cliente.post("/api/auth/login", json={"usuario": USUARIO_SEMBRADO, "clave": CLAVE_SEMBRADA})
    assert respuesta.status_code == 200
    assert respuesta.json()["tipo_token"] == "bearer"
    assert respuesta.json()["duracion_segundos"] == 8 * 3600
    assert consultar("SELECT ultimo_acceso IS NOT NULL FROM usuario WHERE nombre_usuario = %s", (USUARIO_SEMBRADO,)) == [(True,)]


@pytest.mark.parametrize("usuario", ["Admin", "ADMIN"])
def prueba_login_no_distingue_mayusculas_en_el_usuario(cliente: TestClient, usuario: str) -> None:
    respuesta = cliente.post("/api/auth/login", json={"usuario": usuario, "clave": CLAVE_SEMBRADA})
    assert respuesta.status_code == 200


@pytest.mark.parametrize(
    ("usuario", "clave"),
    [("admin", "clave-incorrecta"), ("admin", CLAVE_SEMBRADA.upper()), ("no-existe", CLAVE_SEMBRADA), (" admin", CLAVE_SEMBRADA)],
)
def prueba_login_incorrecto_devuelve_401(cliente: TestClient, usuario: str, clave: str) -> None:
    respuesta = cliente.post("/api/auth/login", json={"usuario": usuario, "clave": clave})
    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(("usuario", "clave"), [("ad\x00min", CLAVE_SEMBRADA), ("admin", CLAVE_SEMBRADA + "\x00")])
def prueba_login_con_caracter_nul_devuelve_422(cliente: TestClient, usuario: str, clave: str) -> None:
    assert cliente.post("/api/auth/login", json={"usuario": usuario, "clave": clave}).status_code == 422


@pytest.mark.parametrize("ruta", ["/api/lecturas", "/api/lecturas/1", "/api/cargas", "/api/cargas/1/rechazos", "/api/torres", "/api/servicios"])
def prueba_rutas_protegidas_sin_token_devuelven_401(cliente: TestClient, ruta: str) -> None:
    assert cliente.get(ruta).status_code == 401


def prueba_token_vencido_devuelve_401(cliente: TestClient) -> None:
    servicio_autenticacion = ServicioAutenticacion(conexion_no_permitida, os.environ["UTILITYHUB_JWT_CLAVE_FIRMA"])
    fecha_inicio_sesion = obtener_fecha_hora_actual_utc() - DURACION_TOKEN - DURACION_TOKEN / 1000
    token_vencido = servicio_autenticacion.emitir_token(USUARIO_SEMBRADO, 1, fecha_inicio_sesion).token_acceso
    respuesta = cliente.get("/api/torres", headers={"Authorization": "Bearer " + token_vencido})
    assert respuesta.status_code == 401


def prueba_historico_paginado_y_ordenado(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    pagina = obtener(cliente, encabezados_autenticados, "/api/lecturas?pagina=2&tamano_pagina=50")
    assert pagina["total_resultados"] == 1429
    assert pagina["total_paginas"] == 29
    assert len(pagina["lecturas"]) == 50
    periodos = [lectura["periodo"] for lectura in pagina["lecturas"]]
    assert periodos == sorted(periodos, reverse=True)
    assert {"nombre_torre", "numero_apartamento", "unidad_medida"} <= pagina["lecturas"][0].keys()


def prueba_historico_solo_anomalos(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    pagina = obtener(cliente, encabezados_autenticados, "/api/lecturas?solo_anomalos=true")
    assert pagina["total_resultados"] == 6
    assert all(lectura["es_anomalo"] for lectura in pagina["lecturas"])


@pytest.mark.parametrize(("torre", "servicio"), [("T01", "AGUA"), ("t01", "agua"), ("T01", "Agua")])
def prueba_historico_filtros_sin_distinguir_mayusculas(
    cliente: TestClient, encabezados_autenticados: dict[str, str], torre: str, servicio: str
) -> None:
    pagina = obtener(
        cliente,
        encabezados_autenticados,
        f"/api/lecturas?torre={torre}&servicio={servicio}&apartamento=301&periodo_desde=2025-12&periodo_hasta=2026-02",
    )
    assert [(lectura["periodo"], lectura["es_anomalo"]) for lectura in pagina["lecturas"]] == [
        ("2026-02", False),
        ("2026-01", True),
        ("2025-12", False),
    ]


@pytest.mark.parametrize(
    "consulta",
    [
        "periodo_desde=2026-05&periodo_hasta=2026-01",
        "periodo_desde=2026-13",
        "tamano_pagina=201",
        "pagina=0",
        "torre=T0%00",
    ],
)
def prueba_historico_con_filtros_invalidos_devuelve_422(
    cliente: TestClient, encabezados_autenticados: dict[str, str], consulta: str
) -> None:
    assert cliente.get(f"/api/lecturas?{consulta}", headers=encabezados_autenticados).status_code == 422


def prueba_detalle_explica_la_anomalia(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    anomala = obtener(cliente, encabezados_autenticados, "/api/lecturas?solo_anomalos=true&torre=T01&servicio=AGUA")["lecturas"][0]
    detalle = obtener(cliente, encabezados_autenticados, f"/api/lecturas/{anomala['id_lectura']}")
    assert detalle["consumo_periodo"] == 26.3
    assert detalle["promedio_referencia"] == 8.25
    assert detalle["umbral_desviacion"] == 0.5
    assert (detalle["limite_inferior_normal"], detalle["limite_superior_normal"]) == (4.125, 12.375)
    assert detalle["desviacion_relativa"] == 2.1879
    assert detalle["fue_evaluada"] is True
    assert detalle["es_anomalo"] is True


def prueba_detalle_de_linea_base_no_se_evalua(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    linea_base = obtener(cliente, encabezados_autenticados, "/api/lecturas?periodo_hasta=2025-10&tamano_pagina=1")["lecturas"][0]
    detalle = obtener(cliente, encabezados_autenticados, f"/api/lecturas/{linea_base['id_lectura']}")
    assert detalle["fue_evaluada"] is False
    assert detalle["consumo_periodo"] is None
    assert detalle["limite_superior_normal"] is None


def prueba_cargas_con_sus_conteos(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    cargas = obtener(cliente, encabezados_autenticados, "/api/cargas")
    assert len(cargas) == 36
    assert sum(carga["filas_aceptadas"] for carga in cargas) == 1429
    assert sum(carga["filas_rechazadas"] for carga in cargas) == 14


def prueba_rechazos_de_una_carga(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    carga = next(
        carga for carga in obtener(cliente, encabezados_autenticados, "/api/cargas")
        if carga["nombre_archivo"] == "lecturas_T01_2026-05.csv"
    )
    rechazos = obtener(cliente, encabezados_autenticados, f"/api/cargas/{carga['id_carga']}/rechazos")
    assert [(rechazo["apartamento"], rechazo["motivo"]) for rechazo in rechazos] == [
        ("502", "tripleta_repetida_en_archivo"),
        ("502", "tripleta_repetida_en_archivo"),
    ]


@pytest.mark.parametrize("ruta", ["/api/lecturas/999999", "/api/cargas/999999/rechazos"])
def prueba_recurso_inexistente_devuelve_404(cliente: TestClient, encabezados_autenticados: dict[str, str], ruta: str) -> None:
    assert cliente.get(ruta, headers=encabezados_autenticados).status_code == 404


def prueba_catalogos(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    assert [torre["codigo"] for torre in obtener(cliente, encabezados_autenticados, "/api/torres")] == ["T01", "T02", "T03"]
    servicios = obtener(cliente, encabezados_autenticados, "/api/servicios")
    assert [(servicio["codigo"], servicio["umbral_desviacion"]) for servicio in servicios] == [("AGUA", 0.5), ("ENERGIA", 0.5)]


def prueba_cors_solo_para_el_origen_configurado(cliente: TestClient) -> None:
    solicitud_previa = {"Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"}
    permitido = cliente.options("/api/lecturas", headers={"Origin": ORIGEN_PERMITIDO, **solicitud_previa})
    ajeno = cliente.options("/api/lecturas", headers={"Origin": "http://otro-sitio.example", **solicitud_previa})
    assert permitido.headers.get("access-control-allow-origin") == ORIGEN_PERMITIDO
    assert "access-control-allow-origin" not in ajeno.headers


def prueba_cors_expone_retry_after(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    respuesta = cliente.get("/api/torres", headers={**encabezados_autenticados, "Origin": ORIGEN_PERMITIDO})
    assert "retry-after" in respuesta.headers.get("access-control-expose-headers", "").lower()


def prueba_fechas_con_zona_utc(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    respuesta_login = cliente.post("/api/auth/login", json={"usuario": USUARIO_SEMBRADO, "clave": CLAVE_SEMBRADA})
    assert respuesta_login.json()["expira_en"].endswith("Z")
    cargas = obtener(cliente, encabezados_autenticados, "/api/cargas")
    assert all(carga["fecha_procesamiento"].endswith("Z") for carga in cargas)
