import pytest

from comun.contrasenas import generar_hash_contrasena, verificar_contrasena


ITERACIONES_RAPIDAS_PARA_PRUEBAS: int = 1_000


def prueba_hash_verifica_la_clave_correcta() -> None:
    hash_almacenado = generar_hash_contrasena("clave-correcta-123", ITERACIONES_RAPIDAS_PARA_PRUEBAS)
    assert verificar_contrasena("clave-correcta-123", hash_almacenado)


def prueba_hash_rechaza_otra_clave() -> None:
    hash_almacenado = generar_hash_contrasena("clave-correcta-123", ITERACIONES_RAPIDAS_PARA_PRUEBAS)
    assert not verificar_contrasena("Clave-correcta-123", hash_almacenado)
    assert not verificar_contrasena("", hash_almacenado)


def prueba_misma_clave_produce_hashes_distintos_por_la_sal() -> None:
    assert generar_hash_contrasena("x" * 12, ITERACIONES_RAPIDAS_PARA_PRUEBAS) != generar_hash_contrasena("x" * 12, ITERACIONES_RAPIDAS_PARA_PRUEBAS)


def prueba_formato_del_hash() -> None:
    algoritmo, iteraciones, _, _ = generar_hash_contrasena("x" * 12).split("$")
    assert algoritmo == "pbkdf2_sha256"
    assert iteraciones == "600000"


@pytest.mark.parametrize(
    "hash_malformado",
    ["", "texto", "md5$1$a$b", "pbkdf2_sha256$no-numero$YQ==$YQ==", "pbkdf2_sha256$1000$no-base64!$YQ==", "pbkdf2_sha256$1000$YQ=="],
)
def prueba_hash_malformado_nunca_verifica(hash_malformado: str) -> None:
    assert not verificar_contrasena("cualquier-clave", hash_malformado)
