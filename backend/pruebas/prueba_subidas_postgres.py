import os
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from api.almacen_local import TAMANO_MAXIMO_OBJETO_BYTES, AlmacenLocal
from api.configuracion import VARIABLE_CARPETA_ALMACEN_LOCAL
from api.main import crear_aplicacion
from comun.excepciones import FirmaDeSubidaInvalida
from pruebas.base_de_datos_de_pruebas import consultar


USUARIO_SEMBRADO: str = "admin"
CLAVE_SEMBRADA: str = "UtilityHub-zXNWjx2EntCE"
ARCHIVO_ULTIMO_PERIODO_T01: str = "lecturas_T01_2026-09.csv"


@pytest.fixture(scope="module")
def carpeta_almacen(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("almacen_local")


@pytest.fixture(scope="module")
def cliente(base_con_lecturas_procesadas: Path, carpeta_almacen: Path) -> Iterator[TestClient]:
    valor_anterior = os.environ.get(VARIABLE_CARPETA_ALMACEN_LOCAL)
    os.environ[VARIABLE_CARPETA_ALMACEN_LOCAL] = str(carpeta_almacen)
    try:
        with TestClient(crear_aplicacion()) as cliente_http:
            yield cliente_http
    finally:
        if valor_anterior is None:
            os.environ.pop(VARIABLE_CARPETA_ALMACEN_LOCAL, None)
        else:
            os.environ[VARIABLE_CARPETA_ALMACEN_LOCAL] = valor_anterior


@pytest.fixture(scope="module")
def encabezados_autenticados(cliente: TestClient) -> dict[str, str]:
    respuesta = cliente.post("/api/auth/login", json={"usuario": USUARIO_SEMBRADO, "clave": CLAVE_SEMBRADA})
    return {"Authorization": "Bearer " + respuesta.json()["token_acceso"]}


def solicitar(cliente: TestClient, encabezados: dict[str, str], nombre_archivo: str) -> Any:
    return cliente.post("/api/subidas", json={"nombre_archivo": nombre_archivo}, headers=encabezados)


def subir(cliente: TestClient, autorizacion: dict[str, Any], contenido: bytes) -> Any:
    return cliente.put(autorizacion["url_subida"], content=contenido, headers=autorizacion["encabezados"])


def prueba_flujo_completo_guarda_el_archivo_y_lo_procesa(
    cliente: TestClient,
    encabezados_autenticados: dict[str, str],
    base_con_lecturas_procesadas: Path,
    carpeta_almacen: Path,
) -> None:
    contenido = (base_con_lecturas_procesadas / ARCHIVO_ULTIMO_PERIODO_T01).read_bytes()
    respuesta_solicitud = solicitar(cliente, encabezados_autenticados, ARCHIVO_ULTIMO_PERIODO_T01)
    assert respuesta_solicitud.status_code == 201, respuesta_solicitud.text
    autorizacion = respuesta_solicitud.json()
    assert autorizacion["metodo"] == "PUT"
    assert autorizacion["clave_objeto"].startswith("entrada/")
    assert autorizacion["clave_objeto"].endswith("/" + ARCHIVO_ULTIMO_PERIODO_T01)
    assert autorizacion["expira_en"].endswith("Z")

    estado_inicial = cliente.get(f"/api/subidas/{autorizacion['id_subida']}", headers=encabezados_autenticados).json()
    assert estado_inicial["estado"] == "pendiente"

    assert subir(cliente, autorizacion, contenido).status_code == 200
    assert (carpeta_almacen / autorizacion["clave_objeto"]).read_bytes() == contenido

    subida = cliente.get(f"/api/subidas/{autorizacion['id_subida']}", headers=encabezados_autenticados).json()
    assert subida["estado"] == "procesada"
    assert subida["detalle_error"] is None
    assert consultar("SELECT nombre_archivo FROM carga WHERE id_carga = %s", (subida["id_carga"],)) == [(ARCHIVO_ULTIMO_PERIODO_T01,)]


def prueba_archivo_con_encabezado_invalido_queda_fallido(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    autorizacion = solicitar(cliente, encabezados_autenticados, ARCHIVO_ULTIMO_PERIODO_T01).json()
    assert subir(cliente, autorizacion, b"columna_rara\n1\n").status_code == 200
    subida = cliente.get(f"/api/subidas/{autorizacion['id_subida']}", headers=encabezados_autenticados).json()
    assert subida["estado"] == "fallida"
    assert subida["id_carga"] is None
    assert "encabezado" in subida["detalle_error"]


def prueba_periodo_anterior_se_rechaza_antes_de_firmar(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    respuesta = solicitar(cliente, encabezados_autenticados, "lecturas_T01_2026-03.csv")
    assert respuesta.status_code == 409
    assert "2026-09" in respuesta.json()["detail"]


@pytest.mark.parametrize(
    "nombre_archivo",
    ["datos.csv", "lecturas_T01_2026-13.csv", "carpeta/lecturas_T01_2026-09.csv", "..\\lecturas_T01_2026-09.csv", " lecturas_T01_2026-09.csv"],
)
def prueba_nombre_de_archivo_invalido_devuelve_422(
    cliente: TestClient,
    encabezados_autenticados: dict[str, str],
    nombre_archivo: str,
) -> None:
    assert solicitar(cliente, encabezados_autenticados, nombre_archivo).status_code == 422


def prueba_torre_inexistente_devuelve_422(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    respuesta = solicitar(cliente, encabezados_autenticados, "lecturas_T09_2026-09.csv")
    assert respuesta.status_code == 422
    assert "T09" in respuesta.json()["detail"]


def prueba_solicitar_subida_sin_token_devuelve_401(cliente: TestClient) -> None:
    assert cliente.post("/api/subidas", json={"nombre_archivo": ARCHIVO_ULTIMO_PERIODO_T01}).status_code == 401
    assert cliente.get("/api/subidas/1").status_code == 401


def prueba_subida_inexistente_devuelve_404(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    assert cliente.get("/api/subidas/999999", headers=encabezados_autenticados).status_code == 404


def prueba_firma_alterada_o_clave_cambiada_devuelve_403(
    cliente: TestClient,
    encabezados_autenticados: dict[str, str],
    carpeta_almacen: Path,
) -> None:
    autorizacion = solicitar(cliente, encabezados_autenticados, ARCHIVO_ULTIMO_PERIODO_T01).json()
    partes_url = urlsplit(autorizacion["url_subida"])
    parametros = {nombre: valores[0] for nombre, valores in parse_qs(partes_url.query).items()}

    firma_alterada = ("0" if parametros["firma"][0] != "0" else "1") + parametros["firma"][1:]
    url_firma_alterada = f"{partes_url.path}?expira={parametros['expira']}&firma={firma_alterada}"
    assert cliente.put(url_firma_alterada, content=b"x").status_code == 403

    url_expira_alterada = f"{partes_url.path}?expira={int(parametros['expira']) + 3600}&firma={parametros['firma']}"
    assert cliente.put(url_expira_alterada, content=b"x").status_code == 403

    url_otra_clave = f"/almacen-local/entrada/otra/{ARCHIVO_ULTIMO_PERIODO_T01}?expira={parametros['expira']}&firma={parametros['firma']}"
    assert cliente.put(url_otra_clave, content=b"x").status_code == 403
    assert not (carpeta_almacen / autorizacion["clave_objeto"]).exists()


def prueba_archivo_demasiado_grande_devuelve_413(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    autorizacion = solicitar(cliente, encabezados_autenticados, ARCHIVO_ULTIMO_PERIODO_T01).json()
    assert subir(cliente, autorizacion, b"x" * (TAMANO_MAXIMO_OBJETO_BYTES + 1)).status_code == 413


def prueba_sin_almacen_configurado_devuelve_503(base_con_lecturas_procesadas: Path) -> None:
    valor_anterior = os.environ.pop(VARIABLE_CARPETA_ALMACEN_LOCAL, None)
    try:
        with TestClient(crear_aplicacion()) as cliente_sin_almacen:
            token = cliente_sin_almacen.post(
                "/api/auth/login", json={"usuario": USUARIO_SEMBRADO, "clave": CLAVE_SEMBRADA}
            ).json()["token_acceso"]
            respuesta = cliente_sin_almacen.post(
                "/api/subidas",
                json={"nombre_archivo": ARCHIVO_ULTIMO_PERIODO_T01},
                headers={"Authorization": "Bearer " + token},
            )
    finally:
        if valor_anterior is not None:
            os.environ[VARIABLE_CARPETA_ALMACEN_LOCAL] = valor_anterior
    assert respuesta.status_code == 503
    assert VARIABLE_CARPETA_ALMACEN_LOCAL in respuesta.json()["detail"]


def prueba_almacen_rechaza_firma_vencida_y_claves_fuera_de_la_carpeta(tmp_path: Path) -> None:
    almacen_local = AlmacenLocal(tmp_path, "clave-de-firma-exclusiva-de-las-pruebas-0123456789")
    fecha_actual = datetime(2026, 10, 8, 12, 0, 0)
    firma = almacen_local.firmar("PUT", "entrada/a/lecturas_T01_2026-09.csv", fecha_actual - timedelta(seconds=1))
    with pytest.raises(FirmaDeSubidaInvalida):
        almacen_local.verificar_firma("PUT", "entrada/a/lecturas_T01_2026-09.csv", firma.expira, firma.firma, fecha_actual)
    firma_vigente = almacen_local.firmar("PUT", "entrada/a/lecturas_T01_2026-09.csv", fecha_actual + timedelta(minutes=5))
    almacen_local.verificar_firma("PUT", "entrada/a/lecturas_T01_2026-09.csv", firma_vigente.expira, firma_vigente.firma, fecha_actual)
    with pytest.raises(FirmaDeSubidaInvalida):
        almacen_local.verificar_firma("GET", "entrada/a/lecturas_T01_2026-09.csv", firma_vigente.expira, firma_vigente.firma, fecha_actual)
    for clave_objeto in ("../fuera.csv", "entrada/../../fuera.csv", ""):
        with pytest.raises(FirmaDeSubidaInvalida):
            almacen_local.guardar_objeto(clave_objeto, b"x")
    assert not (tmp_path.parent / "fuera.csv").exists()

def prueba_archivo_de_carga_subida_se_descarga_con_url_firmada(
    cliente: TestClient,
    encabezados_autenticados: dict[str, str],
    base_con_lecturas_procesadas: Path,
) -> None:
    contenido = (base_con_lecturas_procesadas / ARCHIVO_ULTIMO_PERIODO_T01).read_bytes()
    autorizacion = solicitar(cliente, encabezados_autenticados, ARCHIVO_ULTIMO_PERIODO_T01).json()
    assert subir(cliente, autorizacion, contenido).status_code == 200
    id_carga = cliente.get(f"/api/subidas/{autorizacion['id_subida']}", headers=encabezados_autenticados).json()["id_carga"]

    respuesta_archivo = cliente.get(f"/api/cargas/{id_carga}/archivo", headers=encabezados_autenticados)
    assert respuesta_archivo.status_code == 200, respuesta_archivo.text
    archivo = respuesta_archivo.json()
    assert archivo["nombre_archivo"] == ARCHIVO_ULTIMO_PERIODO_T01
    assert archivo["expira_en"].endswith("Z")

    descarga = cliente.get(archivo["url_descarga"])
    assert descarga.status_code == 200
    assert descarga.content == contenido
    assert descarga.headers["content-type"].startswith("text/csv")


def prueba_firma_de_subida_no_sirve_para_descargar_ni_al_reves(
    cliente: TestClient,
    encabezados_autenticados: dict[str, str],
    base_con_lecturas_procesadas: Path,
) -> None:
    contenido = (base_con_lecturas_procesadas / ARCHIVO_ULTIMO_PERIODO_T01).read_bytes()
    autorizacion = solicitar(cliente, encabezados_autenticados, ARCHIVO_ULTIMO_PERIODO_T01).json()
    assert subir(cliente, autorizacion, contenido).status_code == 200
    assert cliente.get(autorizacion["url_subida"]).status_code == 403

    id_carga = cliente.get(f"/api/subidas/{autorizacion['id_subida']}", headers=encabezados_autenticados).json()["id_carga"]
    url_descarga = cliente.get(f"/api/cargas/{id_carga}/archivo", headers=encabezados_autenticados).json()["url_descarga"]
    assert cliente.put(url_descarga, content=b"reemplazo", headers={"Content-Type": "text/csv"}).status_code == 403


def prueba_carga_sin_archivo_guardado_devuelve_404(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    id_carga_sin_subida = consultar(
        "SELECT MIN(c.id_carga) FROM carga c WHERE NOT EXISTS (SELECT 1 FROM subida s WHERE s.id_carga = c.id_carga)"
    )[0][0]
    respuesta = cliente.get(f"/api/cargas/{id_carga_sin_subida}/archivo", headers=encabezados_autenticados)
    assert respuesta.status_code == 404
    assert "no tiene un archivo" in respuesta.json()["detail"]


def prueba_archivo_de_carga_inexistente_o_sin_token(cliente: TestClient, encabezados_autenticados: dict[str, str]) -> None:
    respuesta = cliente.get("/api/cargas/999999/archivo", headers=encabezados_autenticados)
    assert respuesta.status_code == 404
    assert "no existe" in respuesta.json()["detail"]
    assert cliente.get("/api/cargas/1/archivo").status_code == 401
