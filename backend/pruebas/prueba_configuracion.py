import pytest

from comun.configuracion import VARIABLE_MODO_SSL, cargar_configuracion_desde_entorno
from comun.excepciones import ConfiguracionInvalida


def prueba_modo_ssl_por_defecto_es_prefer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VARIABLE_MODO_SSL, raising=False)
    assert cargar_configuracion_desde_entorno().modo_ssl == "prefer"


@pytest.mark.parametrize("modo_ssl", ["disable", "prefer", "require"])
def prueba_modo_ssl_admitido_se_respeta(monkeypatch: pytest.MonkeyPatch, modo_ssl: str) -> None:
    monkeypatch.setenv(VARIABLE_MODO_SSL, f" {modo_ssl} ")
    assert cargar_configuracion_desde_entorno().modo_ssl == modo_ssl


@pytest.mark.parametrize("modo_ssl", ["verify-full", "REQUIRE", "si"])
def prueba_modo_ssl_no_admitido_se_rechaza(monkeypatch: pytest.MonkeyPatch, modo_ssl: str) -> None:
    monkeypatch.setenv(VARIABLE_MODO_SSL, modo_ssl)
    with pytest.raises(ConfiguracionInvalida):
        cargar_configuracion_desde_entorno()
