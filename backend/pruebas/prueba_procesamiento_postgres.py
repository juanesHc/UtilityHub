import csv
from pathlib import Path

from pruebas.base_de_datos_de_pruebas import consultar


MOTIVO_POR_TIPO_DE_CASO: dict[str, str] = {
    "anomalia": "anomalia",
    "duplicado": "tripleta_repetida_en_archivo",
    "incompleto": "campo_obligatorio_faltante",
    "formato": "lectura_no_numerica",
    "retroceso": "lectura_menor_que_la_anterior",
}
CONSULTA_CONSUMO_NULO: str = (
    "SELECT COUNT(*) FROM lectura l WHERE l.consumo_periodo IS NULL AND {negacion} EXISTS ("
    "SELECT 1 FROM lectura p WHERE p.id_apartamento = l.id_apartamento "
    "AND p.id_servicio = l.id_servicio AND p.periodo < l.periodo)"
)


def leer_casos_esperados(directorio_lecturas: Path) -> set[tuple[str, str, str, str]]:
    with open(directorio_lecturas / "casos_esperados.csv", encoding="utf-8") as archivo:
        return {
            (caso["archivo"], caso["apartamento"], caso["servicio"], MOTIVO_POR_TIPO_DE_CASO[caso["tipo"]])
            for caso in csv.DictReader(archivo)
        }


def leer_hallazgos_de_la_base() -> set[tuple[str, str, str, str]]:
    anomalias = consultar(
        "SELECT c.nombre_archivo, a.numero, s.codigo, 'anomalia' FROM lectura l "
        "JOIN apartamento a USING (id_apartamento) JOIN servicio s USING (id_servicio) "
        "JOIN carga c USING (id_carga) WHERE l.es_anomalo"
    )
    rechazos = consultar(
        "SELECT c.nombre_archivo, r.apartamento, r.servicio, r.motivo FROM rechazo r JOIN carga c USING (id_carga)"
    )
    return {tuple(fila) for fila in anomalias + rechazos}


def prueba_se_procesan_las_36_cargas(base_con_lecturas_procesadas: Path) -> None:
    assert dict(consultar("SELECT estado, COUNT(*) FROM carga GROUP BY estado")) == {
        "procesada_completa": 26,
        "procesada_parcial": 10,
    }


def prueba_lecturas_con_consumo_nulo(base_con_lecturas_procesadas: Path) -> None:
    assert consultar("SELECT COUNT(*) FROM lectura")[0][0] == 1429
    assert consultar(CONSULTA_CONSUMO_NULO.format(negacion="NOT"))[0][0] == 120
    assert consultar(CONSULTA_CONSUMO_NULO.format(negacion=""))[0][0] == 9


def prueba_salen_exactamente_los_casos_esperados(base_con_lecturas_procesadas: Path) -> None:
    casos_esperados = leer_casos_esperados(base_con_lecturas_procesadas)
    hallazgos = leer_hallazgos_de_la_base()
    assert len(casos_esperados) == 17
    assert hallazgos - casos_esperados == set()
    assert casos_esperados - hallazgos == set()


def prueba_conteo_por_tipo_de_caso(base_con_lecturas_procesadas: Path) -> None:
    assert consultar("SELECT COUNT(*) FROM lectura WHERE es_anomalo")[0][0] == 6
    assert dict(consultar("SELECT motivo, COUNT(*) FROM rechazo GROUP BY motivo")) == {
        "tripleta_repetida_en_archivo": 6,
        "campo_obligatorio_faltante": 3,
        "lectura_no_numerica": 3,
        "lectura_menor_que_la_anterior": 2,
    }


def prueba_anomalias_guardan_su_promedio_de_referencia(base_con_lecturas_procesadas: Path) -> None:
    anomalias = consultar("SELECT consumo_periodo, promedio_referencia FROM lectura WHERE es_anomalo")
    assert all(promedio is not None and consumo > promedio * 2 for consumo, promedio in anomalias)


def prueba_nunca_se_viola_la_unicidad(base_con_lecturas_procesadas: Path) -> None:
    assert consultar(
        "SELECT COUNT(*) FROM (SELECT 1 FROM lectura GROUP BY id_apartamento, id_servicio, periodo HAVING COUNT(*) > 1) d"
    )[0][0] == 0
